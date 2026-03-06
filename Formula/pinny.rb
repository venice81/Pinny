class Pinny < Formula
  include Language::Python::Virtualenv

  desc "TUI/CLI wrapper for xcrun simctl location"
  homepage "https://github.com/venice81/Pinny"
  url "https://github.com/venice81/Pinny/archive/refs/tags/0.1.1.tar.gz"
  sha256 "806c783700958e53ca929bb2a310c1186270d683955730ed676b8b881a24e63d"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "pinny", shell_output("#{bin}/pinny --help")
  end
end
