{ config
, pkgs
, lib
, ...
}:
{
  options.clan.localsend = {
    enable = lib.mkEnableOption (lib.mdDoc "enable the localsend module");
    defaultLocation = lib.mkOption {
      type = lib.types.str;
      description = "The default download location";
    };
    package = lib.mkPackageOption pkgs "localsend" { };
  };

  imports =
    if config.clan.localsend.enable then
      [
        {
          clanCore.state.localsend.folders = [
            "/var/localsend"
            config.clan.localsend.defaultLocation
          ];
          environment.systemPackages = [ config.clan.localsend.package ];

          networking.firewall.interfaces."zt+".allowedTCPPorts = [ 53317 ];
          networking.firewall.interfaces."zt+".allowedUDPPorts = [ 53317 ];

          #TODO: This is currently needed because there is no ipv6 multicasting support yet
          #
          systemd.network.networks."09-zerotier" = {
            networkConfig = {
              Address = "192.168.56.2/24";
            };
          };
        }
      ]
    else
      [ ];
}
