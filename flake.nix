{
  description = "Nix expressions for defining Replit development environments";
  inputs.nixpkgs.url = "github:nixos/nixpkgs?rev=52e3e80afff4b16ccb7c52e9f0f5220552f03d04";

  outputs = { self, nixpkgs, ... }:
    let
      mkPkgs = system: import nixpkgs {
        inherit system;
      };
      pkgs = mkPkgs "x86_64-linux";
    in
    {
      packages.x86_64-linux.default = pkgs.mkShell {
        packages = [
          pkgs.python310Full
          pkgs.toml2json
          pkgs.jq
        ];
      };
    };
}