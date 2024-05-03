{
  pkgs,
  lib,
  config,
  ...
}:
{
  options.clan.zt-tcp-relay = {
    port = lib.mkOption {
      type = lib.types.port;
      default = 4443;
      description = "Port to listen on";
    };
  };
  config = {
    networking.firewall.allowedTCPPorts = [ config.clan.zt-tcp-relay.port ];

    systemd.services.zt-tcp-relay = {
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];
      serviceConfig = {
        ExecStart = "${
          pkgs.callPackage ../../pkgs/zt-tcp-relay { }
        }/bin/zt-tcp-relay --listen [::]:${builtins.toString config.clan.zt-tcp-relay.port}";
        Restart = "always";
        RestartSec = "5";
        dynamicUsers = true;
      };
    };
  };
}
