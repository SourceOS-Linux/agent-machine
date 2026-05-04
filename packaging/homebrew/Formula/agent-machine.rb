class AgentMachine < Formula
  desc "SourceOS Agent Machine local and cluster node substrate CLI"
  homepage "https://github.com/SourceOS-Linux/agent-machine"
  url "https://github.com/SourceOS-Linux/agent-machine.git", branch: "main"
  version "0.1.0-dev"
  license "MIT"
  head "https://github.com/SourceOS-Linux/agent-machine.git", branch: "main"

  def install
    bin.install "bin/agent-machine"
    chmod 0755, bin/"agent-machine"

    pkgshare.install "contracts"
    pkgshare.install "docs"
    pkgshare.install "examples"
  end

  def caveats
    <<~EOS
      Agent Machine installed the bootstrap CLI:
        agent-machine version
        agent-machine paths
        agent-machine probe --format json

      This formula installs contracts, docs, and examples under:
        #{pkgshare}

      Runtime directories are not created automatically yet. The future installer
      lane will manage /etc/agent-machine, /var/lib/agent-machine, and
      /run/agent-machine through SourceOS policy-aware setup commands.
    EOS
  end

  test do
    assert_match "agent-machine", shell_output("#{bin}/agent-machine version")
    probe = shell_output("#{bin}/agent-machine probe --format json")
    assert_match '"kind": "AgentMachineProbe"', probe
    assert_match '"secretValuesIncluded": false', probe
  end
end
