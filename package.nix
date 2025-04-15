{
  lib,
  python3Packages,
  fetchFromGitHub,
  python3,
}:
python3Packages.buildPythonApplication {
  pname = "gpt-cli";
  version = "0.3.2";
  format = "pyproject";

  preBuild = ''
    substituteInPlace pyproject.toml \
      --replace 'anthropic~=0.44.0' 'anthropic' \
      --replace 'black~=24.10.0' 'black' \
      --replace 'google-generativeai~=0.8.4' 'google-generativeai' \
      --replace 'openai~=1.60.0' 'openai' \
      --replace 'pydantic<2' 'pydantic'
  '';

  nativeBuildInputs = with python3.pkgs; [
    pip
    setuptools
    wheel
  ];

  propagatedBuildInputs = with python3.pkgs; [
    anthropic
    attrs
    black
    cohere
    google-generativeai
    openai
    prompt-toolkit
    pytest
    pyyaml
    rich
    typing-extensions
    pydantic
  ];

  src = fetchFromGitHub {
    owner = "kharvd";
    repo = "gpt-cli";
    rev = "08b535cb459f2f2269d8889de297f7f995d800f4";
    sha256 = "sha256-Zmqhdh+XMvJ3bhW+qkQOJT3nf+8luv7aJGW6xJSPuns=";
  };

  meta = with lib; {
    description = "Command-line interface for ChatGPT, Claude and Bard";
    homepage = "https://github.com/kharvd/gpt-cli";
    license = licenses.mit;
    maintainers = with maintainers; [_404wolf];
  };
}
