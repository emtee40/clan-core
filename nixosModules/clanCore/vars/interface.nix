{
  lib,
  config,
  pkgs,
  ...
}:
let
  inherit (lib) mkOption;
  inherit (lib.types)
    attrsOf
    bool
    either
    enum
    listOf
    package
    path
    str
    submoduleWith
    ;
  # the original types.submodule has strange behavior
  submodule =
    module:
    submoduleWith {
      specialArgs.pkgs = pkgs;
      modules = [ module ];
    };
  options = lib.mapAttrs (_: mkOption);
in
{
  options = {
    settings = import ./settings-opts.nix { inherit lib; };
    generators = lib.mkOption {
      description = ''
        A set of generators that can be used to generate files.
        Generators are scripts that produce files based on the values of other generators and user input.
        Each generator is expected to produce a set of files under a directory.
      '';
      default = { };
      type = attrsOf (submodule {
        imports = [ ./generator.nix ];
        options = options {
          dependencies = {
            description = ''
              A list of other generators that this generator depends on.
              The output values of these generators will be available to the generator script as files.
              For example, the file 'file1' of a dependency named 'dep1' will be available via $dependencies/dep1/file1.
            '';
            type = listOf str;
            default = [ ];
          };
          files = {
            description = ''
              A set of files to generate.
              The generator 'script' is expected to produce exactly these files under $out.
            '';
            type = attrsOf (
              submodule (file: {
                imports = [ config.settings.fileModule ];
                options = options {
                  name = {
                    type = lib.types.str;
                    description = ''
                      name of the public fact
                    '';
                    readOnly = true;
                    default = file.config._module.args.name;
                  };
                  secret = {
                    description = ''
                      Whether the file should be treated as a secret.
                    '';
                    type = bool;
                    default = true;
                  };
                  path = {
                    description = ''
                      The path to the file containing the content of the generated value.
                      This will be set automatically
                    '';
                    type = str;
                    readOnly = true;
                  };
                  value = {
                    description = ''
                      The content of the generated value.
                      Only available if the file is not secret.
                    '';
                    type = str;
                    default = throw "Cannot access value of secret file";
                    defaultText = "Throws error because the value of a secret file is not accessible";
                  };
                };
              })
            );
          };
          prompts = {
            description = ''
              A set of prompts to ask the user for values.
              Prompts are available to the generator script as files.
              For example, a prompt named 'prompt1' will be available via $prompts/prompt1
            '';
            type = attrsOf (submodule {
              options = {
                description = {
                  description = ''
                    The description of the prompted value
                  '';
                  type = str;
                  example = "SSH private key";
                };
                type = {
                  description = ''
                    The input type of the prompt.
                    The following types are available:
                      - hidden: A hidden text (e.g. password)
                      - line: A single line of text
                      - multiline: A multiline text
                  '';
                  type = enum [
                    "hidden"
                    "line"
                    "multiline"
                  ];
                  default = "line";
                };
              };
            });
          };
          runtimeInputs = {
            description = ''
              A list of packages that the generator script requires.
              These packages will be available in the PATH when the script is run.
            '';
            type = listOf package;
            default = [ ];
          };
          script = {
            description = ''
              The script to run to generate the files.
              The script will be run with the following environment variables:
                - $dependencies: The directory containing the output values of all declared dependencies
                - $out: The output directory to put the generated files
                - $prompts: The directory containing the prompted values as files
              The script should produce the files specified in the 'files' attribute under $out.
            '';
            type = either str path;
          };
          finalScript = {
            description = ''
              The final generator script, wrapped, so:
                - all required programs are in PATH
                - sandbox is set up correctly
            '';
            type = lib.types.str;
            readOnly = true;
            internal = true;
            visible = false;
          };
        };
      });
    };
  };
}
