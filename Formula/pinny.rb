class Pinny < Formula
  include Language::Python::Virtualenv

  desc "TUI/CLI wrapper for xcrun simctl location"
  homepage "https://github.com/venice81/Pinny"
  url "https://github.com/venice81/Pinny/archive/refs/tags/0.1.2.tar.gz"
  sha256 "5a9624f6777fcc7d44c5453b99e350c744de3729cc1dd02f4d9d8975627e50aa"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "pinny", shell_output("#{bin}/pinny --help")
  end
end
