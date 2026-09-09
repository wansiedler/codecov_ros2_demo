# Copyright 2026 Alexander Paul Wansiedler
# SPDX-License-Identifier: Apache-2.0

# shellcheck shell=bash
# Interactive shell in the dev container. Non-interactive invocations (the
# compose `test` service, `docker compose exec dev make ...`) return here at
# once: the entrypoint already sourced ROS for them.
case $- in
  *i*) ;;
  *) return ;;
esac

HISTFILESIZE=200000
HISTSIZE=100000
HISTCONTROL=ignoreboth
shopt -s histappend checkwinsize

# oh-my-bash, cloned at a pinned commit by the Dockerfile; the shell works
# without it, only plainer.
export OSH="$HOME/.oh-my-bash"
if [ -f "$OSH/oh-my-bash.sh" ]; then
  # shellcheck disable=SC2034  # the three are read by oh-my-bash.sh
  OSH_THEME="agnoster"
  # shellcheck disable=SC2034
  DISABLE_AUTO_UPDATE="true"
  # shellcheck disable=SC2034
  OMB_USE_SUDO=true
  # shellcheck disable=SC2034  # read by oh-my-bash.sh
  completions=(git ssh)
  # shellcheck disable=SC2034
  aliases=(general)
  # shellcheck disable=SC2034
  plugins=(git)
  # shellcheck disable=SC1091
  source "$OSH/oh-my-bash.sh"
fi

# After oh-my-bash, so these win over its `general` alias set.
alias ll='ls -lah --color=auto --time-style=+%d.%m.%y'
alias l='ls -CF --color=auto'
alias la='ls -A'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
alias gst='git status'
alias glog='git log --oneline --graph --decorate --all'
alias ws='cd ~/ws'

# The whale marks a container prompt so a host terminal is never mistaken for one.
__container_prompt() {
  [[ "$PS1" == "🐳"* ]] || PS1="🐳$PS1"
}
case ";$PROMPT_COMMAND;" in
  *";__container_prompt;"*) ;;
  *) PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND;}__container_prompt" ;;
esac

# shellcheck disable=SC1091
[ -f /usr/share/bash-completion/bash_completion ] && source /usr/share/bash-completion/bash_completion
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
if [ -f "$HOME/ws/install/local_setup.bash" ]; then
  # shellcheck disable=SC1091
  source "$HOME/ws/install/local_setup.bash"
else
  echo "no install/ yet - run: colcon build   (or: make build)"
fi
