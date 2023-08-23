{ self, runCommand, check-jsonschema, pkgs, lib, ... }:
let
  clanModules = self.clanModules;

  baseModule = {
    imports =
      (import (pkgs.path + "/nixos/modules/module-list.nix"))
      ++ [{
        nixpkgs.hostPlatform = "x86_64-linux";
      }];
  };

  optionsFromModule = module:
    let
      evaled = lib.evalModules {
        modules = [ module baseModule ];
      };
    in
    evaled.options.clan.networking;

  clanModuleSchemas = lib.mapAttrs (_: module: self.lib.jsonschema.parseOptions (optionsFromModule module)) clanModules;

  mkTest = name: schema: runCommand "schema-${name}" { } ''
    ${check-jsonschema}/bin/check-jsonschema \
      --check-metaschema ${builtins.toFile "schema-${name}" (builtins.toJSON schema)}
      touch $out
  '';
in
lib.mapAttrs'
  (name: schema: {
    name = "schema-${name}";
    value = mkTest name schema;
  })
  clanModuleSchemas
