{ self, inputs, ... }:
{
  flake.templates = {
    new-clan = {
      description = "Initialize a new clan flake";
      path = ./new-clan;
    };
    empty = {
      description = "A empty clan template. Primarily for usage with the clan ui";
      path = ./empty;
    };
    default = self.templates.new-clan;
    minimal = {
      description = "for clans managed via (G)UI";
      path = ./minimal;
    };
  };
  flake.checks.x86_64-linux.template-minimal =
    let
      path = self.templates.minimal.path;
      initialized = inputs.nixpkgs.legacyPackages.x86_64-linux.runCommand "minimal-clan-flake" { } ''
        mkdir $out
        cp -r ${path}/* $out
        mkdir -p $out/machines/foo
        echo '{ "nixpkgs": { "hostPlatform": "x86_64-linux" } }' > $out/machines/foo/settings.json
      '';
      evaled = (import "${initialized}/flake.nix").outputs {
        self = evaled // {
          outPath = initialized;
        };
        clan-core = self;
      };
    in
    evaled.nixosConfigurations.foo.config.system.build.vm;
}
