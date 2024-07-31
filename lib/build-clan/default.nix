## WARNING: Do not add core logic here.
## This is only a wrapper such that buildClan can be called as a function.
## Add any logic to ./module.nix
{
  lib,
  nixpkgs,
  clan-core,
}:
{
  ## Inputs
  directory, # The directory containing the machines subdirectory # allows to include machine-specific modules i.e. machines.${name} = { ... }
  # A map from arch to pkgs, if specified this nixpkgs will be only imported once for each system.
  # This improves performance, but all nipxkgs.* options will be ignored.
  inventory ? { },
  ## Sepcial inputs (not passed to the module system as config)
  specialArgs ? { }, # Extra arguments to pass to nixosSystem i.e. useful to make self available # A set containing clan meta: name :: string, icon :: string, description :: string
  ##
  ...
}@attrs:
let
  eval = import ./eval.nix {
    inherit
      lib
      nixpkgs
      specialArgs
      clan-core
      ;
  } { self = directory; };
  meta = attrs.meta or { };
  rest = builtins.removeAttrs attrs [
    "meta"
    "specialArgs"
  ];
in
eval {
  inventory.meta = lib.mapAttrs (_: lib.mkDefault) meta;
  imports = [
    rest
    # implementation
    ./module.nix

    # Explicit output, usually defined by flake-parts
    { options.nixosConfigurations = lib.mkOption { type = lib.types.raw; }; }
  ];
}
