{
  lib,
  config,
  pkgs,
  ...
}:
let
  inherit (lib.types) submoduleWith;
  submodule =
    module:
    submoduleWith {
      specialArgs.pkgs = pkgs;
      modules = [ module ];
    };
in
{
  imports = [
    ./public/in_repo.nix
    # ./public/vm.nix
    # ./secret/password-store.nix
    ./secret/sops.nix
    # ./secret/vm.nix
  ];
  options.clan.core.vars = lib.mkOption {
    visible = false;
    description = ''
      Generated Variables

      Define generators that prompt for or generate variables like facts and secrets to store, deploy, and rotate them easily.
      For example, generators can be used to:
        - prompt the user for input, like passwords or host names
        - generate secrets like private keys automatically when they are needed
        - output multiple values like private and public keys simultaneously
    '';
    type = submodule { imports = [ ./interface.nix ]; };
  };

  config.system.clan.deployment.data = {
    vars = {
      generators = lib.flip lib.mapAttrs config.clan.core.vars.generators (
        _name: generator: {
          inherit (generator) dependencies finalScript prompts;
          files = lib.flip lib.mapAttrs generator.files (_name: file: { inherit (file) secret; });
        }
      );
      inherit (config.clan.core.vars.settings) secretUploadDirectory secretModule publicModule;
    };
    inherit (config.clan.core.networking) targetHost buildHost;
    inherit (config.clan.core.deployment) requireExplicitUpdate;
  };
}
