{ config, lib, pkgs, ... }:
let
  cfg = config.clan.borgbackup;
in
{
  options.clan.borgbackup = {
    enable = lib.mkEnableOption "backups with borgbackup";
    destinations = lib.mkOption {
      type = lib.types.attrsOf (lib.types.submodule ({ name, ... }: {
        options = {
          name = lib.mkOption {
            type = lib.types.str;
            default = name;
            description = "the name of the backup job";
          };
          repo = lib.mkOption {
            type = lib.types.str;
            description = "the borgbackup repository to backup to";
          };
          rsh = lib.mkOption {
            type = lib.types.str;
            default = "ssh -i ${config.clanCore.secrets.borgbackup.secrets."borgbackup.ssh".path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null";
            description = "the rsh to use for the backup";
          };

        };
      }));
      description = ''
        destinations where the machine should be backuped to
      '';
    };
  };
  config = lib.mkIf cfg.enable {
    services.borgbackup.jobs = lib.mapAttrs
      (_: dest: {
        paths = lib.flatten (map (state: state.folders) (lib.attrValues config.clanCore.state));
        exclude = [
          "*.pyc"
        ];
        repo = dest.repo;
        environment.BORG_RSH = dest.rsh;
        encryption.mode = "none";
        compression = "auto,zstd";
        startAt = "*-*-* 01:00:00";
        preHook = ''
          set -x
        '';

        prune.keep = {
          within = "1d"; # Keep all archives from the last day
          daily = 7;
          weekly = 4;
          monthly = 0;
        };
      })
      cfg.destinations;

    clanCore.secrets.borgbackup = {
      facts."borgbackup.ssh.pub" = { };
      secrets."borgbackup.ssh" = { };
      generator.path = [ pkgs.openssh pkgs.coreutils ];
      generator.script = ''
        ssh-keygen -t ed25519 -N "" -f "$secrets"/borgbackup.ssh
        mv "$secrets"/borgbackup.ssh.pub "$facts"/borgbackup.ssh.pub
      '';
    };

    clanCore.backups.providers.borgbackup = {
      list = ''
        ssh ${config.clan.networking.deploymentAddress} <<EOF
          ${lib.concatMapStringsSep "\n" (dest: ''
            borg-job-${dest.name} list --json | jq -r '. + {"job-name": "${dest.name}"}'
          '') (lib.attrValues cfg.destinations)}
        EOF
      '';
      start = ''
        ssh ${config.clan.networking.deploymentAddress} -- '
          ${lib.concatMapStringsSep "\n" (dest: ''
            systemctl start borgbackup-job-${dest.name}
          '') (lib.attrValues cfg.destinations)}
        '
      '';

      restore = ''
        ssh ${config.clan.networking.deploymentAddress} -- LOCATION="$LOCATION" ARCHIVE="$ARCHIVE_ID" JOB="$JOB" '
          set -efux
          cd /
          borg-job-"$JOB" extract --list --dry-run "$LOCATION"::"$ARCHIVE"
        '
      '';
    };
  };
}
