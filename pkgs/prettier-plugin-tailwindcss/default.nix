{ lib, buildNpmPackage, fetchFromGitHub }:

buildNpmPackage rec {
  pname = "prettier-plugin-tailwindcss";
  version = "0.5.3";

  src = fetchFromGitHub {
    owner = "tailwindlabs";
    repo = "prettier-plugin-tailwindcss";
    rev = "v${version}";
    hash = "sha256-qzpsO9aAdW1odvaPvzTANa5wYs4CcrIYwYdJDTFSJnw=";
  };

  npmDepsHash = "sha256-PxQWsw6r2rb+QMXWU4uXFVIyHt6i+Xyc4rNyzHS8++M=";

  meta = with lib; {
    description = "Prettier plugin for Tailwind CSS that automatically sorts classes";
    homepage = "https://github.com/tailwindlabs/prettier-plugin-tailwindcss";
    license = licenses.mit;
  };
}
