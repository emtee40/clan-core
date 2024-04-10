{ self, ... }:
{
  imports = [
    ./impure/flake-module.nix
    ./backups/flake-module.nix
    ./installation/flake-module.nix
    ./flash/flake-module.nix
  ];
  perSystem =
    {
      pkgs,
      lib,
      self',
      ...
    }:
    {
      checks =
        let
          # ensure all options can be rendered after importing clan into nixos
          renderClanOptions =
            let
              docs = pkgs.nixosOptionsDoc {
                options =
                  (pkgs.nixos {
                    imports = [ self.nixosModules.clanCore ];
                    clanCore.clanDir = ./.;
                  }).options;
                warningsAreErrors = false;
              };
            in
            docs.optionsJSON;
          nixosTestArgs = {
            # reference to nixpkgs for the current system
            inherit pkgs;
            # this gives us a reference to our flake but also all flake inputs
            inherit self;
          };
          nixosTests = lib.optionalAttrs (pkgs.stdenv.isLinux) {
            # import our test
            secrets = import ./secrets nixosTestArgs;
            container = import ./container nixosTestArgs;
            deltachat = import ./deltachat nixosTestArgs;
            matrix-synapse = import ./matrix-synapse nixosTestArgs;
            zt-tcp-relay = import ./zt-tcp-relay nixosTestArgs;
            borgbackup = import ./borgbackup nixosTestArgs;
            syncthing = import ./syncthing nixosTestArgs;
            wayland-proxy-virtwl = import ./wayland-proxy-virtwl nixosTestArgs;
          };
          schemaTests = pkgs.callPackages ./schemas.nix { inherit self; };

          flakeOutputs =
            lib.mapAttrs' (
              name: config: lib.nameValuePair "nixos-${name}" config.config.system.build.toplevel
            ) self.nixosConfigurations
            // lib.mapAttrs' (n: lib.nameValuePair "package-${n}") self'.packages
            // lib.mapAttrs' (n: lib.nameValuePair "devShell-${n}") self'.devShells
            // lib.mapAttrs' (name: config: lib.nameValuePair "home-manager-${name}" config.activation-script) (
              self'.legacyPackages.homeConfigurations or { }
            );
        in
        { inherit renderClanOptions; } // nixosTests // schemaTests // flakeOutputs;
      legacyPackages = {
        nixosTests =
          let
            nixosTestArgs = {
              # reference to nixpkgs for the current system
              inherit pkgs;
              # this gives us a reference to our flake but also all flake inputs
              inherit self;
            };
          in
          lib.optionalAttrs (pkgs.stdenv.isLinux) {
            # import our test
            secrets = import ./secrets nixosTestArgs;
            container = import ./container nixosTestArgs;
          };
      };
    };
}
