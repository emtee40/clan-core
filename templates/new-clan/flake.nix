{
  description = "<Put your description here>";

  inputs = {
    clan-core.url = "git+https://git.clan.lol/clan/clan-core";
  };

  outputs = inputs @ { flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        ./clan-flake-module.nix
      ];
    };
}
