{ pkgs, config, ... }:
{
  users.mutableUsers = false;
  users.extraUsers.root.hashedPasswordFile = "/run/secrets-for-users/passwordHash";
  sops.secrets."${config.clanCore.machineName}-passwordHash".neededForUsers = true;
  clanCore.facts.services.password = {
    secret.password = { };
    secret.passwordHash = { };
    generator.path = with pkgs; [
      coreutils
      xkcdpass
      mkpasswd
    ];
    generator.script = ''
      xkcdpass -c 3 -d -  > $secrets/password
      cat $secrets/password | mkpasswd -s -m sha-512 > $secrets/passwordHash
    '';
  };
}