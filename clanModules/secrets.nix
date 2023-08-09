{ config, lib, ... }:
let
  cfg = config.clan.secrets;
in
{
  options.clan.secrets = lib.mkOption {
    type = lib.types.attrsOf
      (lib.types.submodule (secret: {
        name = lib.mkOption {
          type = lib.types.str;
          default = secret.name;
          description = ''
            filename of the secret
          '';
        };
        generator = lib.mkOption {
          type = lib.types.nullOr lib.types.str;
          description = ''
            script to generate the secret.
            can be set to null. then the user has to provide the secret via the clan cli
          '';
        };
        path = lib.mkOption {
          type = lib.types.str;
          description = ''
            path where the secret is located in the filesystem
          '';
          default = "/run/secrets/${secret.config.name}";
        };
      }))
      };
  }
