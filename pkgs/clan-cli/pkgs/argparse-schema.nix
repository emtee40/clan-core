{ lib
, python3
, fetchFromGitHub
}:

python3.pkgs.buildPythonPackage {
  pname = "argparse-schema";
  version = "unstable-2019-06-27";
  format = "setuptools";

  src = fetchFromGitHub {
    owner = "FebruaryBreeze";
    repo = "argparse-schema";
    rev = "cb4634e199acf6300654868ed704fedf44ca710d";
    hash = "sha256-Cu3g9rGogG8PqPCK+r9cmmAh/vIad1xBgsT/7shDpG4=";
  };

  pythonImportsCheck = [ "argparse_schema" ];

  meta = with lib; {
    description = "Argument Parse with JSON Schema Support";
    homepage = "https://github.com/FebruaryBreeze/argparse-schema";
    license = licenses.mit;
    maintainers = with maintainers; [ ];
  };
}
