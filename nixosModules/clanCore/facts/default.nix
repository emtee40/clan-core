{
  config,
  lib,
  pkgs,
  ...
}:
{
  options.clanCore.facts = {
    secretStore = lib.mkOption {
      type = lib.types.enum [
        "sops"
        "password-store"
        "vm"
        "custom"
      ];
      default = "sops";
      description = ''
        method to store secret facts
        custom can be used to define a custom secret fact store.
      '';
    };

    secretModule = lib.mkOption {
      type = lib.types.str;
      internal = true;
      description = ''
        the python import path to the secret module
      '';
    };

    secretUploadDirectory = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = ''
        The directory where secrets are uploaded into, This is backend specific.
      '';
    };

    secretPathFunction = lib.mkOption {
      type = lib.types.raw;
      description = ''
        The function to use to generate the path for a secret.
        The default function will use the path attribute of the secret.
        The function will be called with the secret submodule as an argument.
      '';
    };

    publicStore = lib.mkOption {
      type = lib.types.enum [
        "in_repo"
        "vm"
        "custom"
      ];
      default = "in_repo";
      description = ''
        method to store public facts.
        custom can be used to define a custom public fact store.
      '';
    };
    publicModule = lib.mkOption {
      type = lib.types.str;
      internal = true;
      description = ''
        the python import path to the public module
      '';
    };
    publicDirectory = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
    };

    services = lib.mkOption {
      default = { };
      type = lib.types.attrsOf (
        lib.types.submodule (service: {
          options = {
            name = lib.mkOption {
              type = lib.types.str;
              default = service.config._module.args.name;
              description = ''
                Namespace of the service
              '';
            };
            generator = lib.mkOption {
              type = lib.types.submodule (
                { config, ... }:
                {
                  options = {
                    path = lib.mkOption {
                      type = lib.types.listOf (lib.types.either lib.types.path lib.types.package);
                      default = [ ];
                      description = ''
                        Extra paths to add to the PATH environment variable when running the generator.
                      '';
                    };
                    prompt = lib.mkOption {
                      type = lib.types.nullOr lib.types.str;
                      default = null;
                      description = ''
                        prompt text to ask for a value.
                        This value will be passed to the script as the environment variable $prompt_value.
                      '';
                    };
                    script = lib.mkOption {
                      type = lib.types.str;
                      description = ''
                        Shell script snippet to generate the secrets and facts.
                        The script has access to the following environment variables:
                        - facts: path to a directory where facts can be stored
                        - secrets: path to a directory where secrets can be stored
                        The script is expected to generate all secrets and facts defined for this service.
                      '';
                    };
                    finalScript = lib.mkOption {
                      type = lib.types.str;
                      readOnly = true;
                      internal = true;
                      default = ''
                        set -eu -o pipefail

                        export PATH="${lib.makeBinPath config.path}:${pkgs.coreutils}/bin"

                        # prepare sandbox user
                        mkdir -p /etc
                        cp ${
                          pkgs.runCommand "fake-etc" { } ''
                            export PATH="${pkgs.coreutils}/bin"
                            mkdir -p $out
                            cp /etc/* $out/
                          ''
                        }/* /etc/

                        ${config.script}
                      '';
                    };
                  };
                }
              );
            };
            secret = lib.mkOption {
              default = { };
              type = lib.types.attrsOf (
                lib.types.submodule (secret: {
                  options =
                    {
                      name = lib.mkOption {
                        type = lib.types.str;
                        description = ''
                          name of the secret
                        '';
                        default = secret.config._module.args.name;
                      };
                      path = lib.mkOption {
                        type = lib.types.str;
                        description = ''
                          path to a secret which is generated by the generator
                        '';
                        default = config.clanCore.facts.secretPathFunction secret;
                      };
                    }
                    // lib.optionalAttrs (config.clanCore.facts.secretModule == "clan_cli.facts.secret_modules.sops") {
                      groups = lib.mkOption {
                        type = lib.types.listOf lib.types.str;
                        default = config.clanCore.sops.defaultGroups;
                        description = ''
                          Groups to decrypt the secret for. By default we always use the user's key.
                        '';
                      };
                    };
                })
              );
              description = ''
                path where the secret is located in the filesystem
              '';
            };
            public = lib.mkOption {
              default = { };
              type = lib.types.attrsOf (
                lib.types.submodule (fact: {
                  options = {
                    name = lib.mkOption {
                      type = lib.types.str;
                      description = ''
                        name of the public fact
                      '';
                      default = fact.config._module.args.name;
                    };
                    path = lib.mkOption {
                      type = lib.types.path;
                      description = ''
                        path to a fact which is generated by the generator
                      '';
                      defaultText = lib.literalExpression "\${config.clanCore.clanDir}/machines/\${config.clanCore.machineName}/facts/\${fact.config.name}";
                      default =
                        config.clanCore.clanDir + "/machines/${config.clanCore.machineName}/facts/${fact.config.name}";
                    };
                    value = lib.mkOption {
                      defaultText = lib.literalExpression "\${config.clanCore.clanDir}/\${fact.config.path}";
                      type = lib.types.nullOr lib.types.str;
                      default =
                        if builtins.pathExists fact.config.path then lib.strings.fileContents fact.config.path else null;
                    };
                  };
                })
              );
            };
          };
        })
      );
    };
  };
  imports = [
    ./compat.nix

    ./secret/sops.nix
    ./secret/password-store.nix
    ./secret/vm.nix

    ./public/in_repo.nix
    ./public/vm.nix
  ];
}
