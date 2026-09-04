{
  description = "nix-my-gnome (nmg) -- convert a dconf dump into a home-manager dconf.settings module";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        nmg = pkgs.python3Packages.buildPythonApplication {
          pname = "nix-my-gnome";
          version = "0.1.0";
          pyproject = true;
          src = ./.;
          build-system = [ pkgs.python3Packages.setuptools ];
          # No runtime deps beyond the Python standard library.
          nativeCheckInputs = [ pkgs.python3Packages.pytestCheckHook ];
        };
      in
      {
        packages.default = nmg;
        packages.nmg = nmg;

        apps.default = {
          type = "app";
          program = "${nmg}/bin/nmg";
        };

        devShells.default = pkgs.mkShell {
          packages = [ pkgs.python3 pkgs.python3Packages.pytest ];
        };
      });
}
