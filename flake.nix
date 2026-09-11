{
  description = "Meowderator";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = {
    nixpkgs,
    flake-utils,
    ...
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};

      python = pkgs.python313;

      nativeBuildInputs = with pkgs; [sqlite python] ++ (with python.pkgs; [
        (disnake.overrideAttrs (old: {
         version = "2.12.1";
         src = pkgs.fetchFromGitHub {
           owner = "DisnakeDev";
           repo = "disnake";
           rev = "v2.12.1";
           hash = "sha256-0tFd8GXdUM2Pja/9UHGJ1V0i3BEabUhR/7BnM2OCebc=";
         };
         nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ hatchling  hatch-vcs versioningit ];
         dependencies = [ typing-extensions aiohttp ];
        doCheck = false;
          doInstallCheck = false;
         dontCheckRuntimeDeps = true;
       }))
      ]);

      buildInputs = with pkgs; [];
    in {
      formatter = pkgs.alejandra;
      devShells.default =
        pkgs.mkShell {inherit nativeBuildInputs buildInputs;};
    });
}
