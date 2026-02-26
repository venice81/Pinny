class Pinny < Formula
  include Language::Python::Virtualenv

  desc "TUI wrapper for xcrun simctl location"
  homepage "https://github.com/your-org/pinny"
  url "https://github.com/your-org/pinny/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    output = shell_output("#{bin}/pinny download")
    assert_match "[", output
  end
end
