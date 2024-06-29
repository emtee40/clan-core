{ lib, ... }:
let
  inherit (lib) mkOption;
  inherit (lib.types)
    attrsOf
    bool
    enum
    listOf
    str
    submodule
    ;
  options = lib.mapAttrs (_: mkOption);
  subOptions = opts: submodule { options = options opts; };
in
{
  options = options {
    generators = {
      type = attrsOf (subOptions {
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
          type = attrsOf (subOptions {
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
          });
        };
        prompts = {
          description = ''
            A set of prompts to ask the user for values.
            Prompts are available to the generator script as files.
            For example, a prompt named 'prompt1' will be available via $prompts/prompt1
          '';
          type = attrsOf (subOptions {
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
          });
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
          type = str;
        };
      });
    };
  };
}