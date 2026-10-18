#!/usr/bin/env bash
# Stepwise: walks you through building your own app, one stage at a time.
# Usage: stepwise.sh [project-dir]
# Kept bash 3.2 compatible (macOS default): no namerefs, assoc arrays or ${var,,}.

set -u

TOTAL_STAGES=10
LAST_BUILT_STAGE=4

if [[ -t 1 ]]; then
  BOLD=$'\e[1m' DIM=$'\e[2m' CYAN=$'\e[36m' GREEN=$'\e[32m' YELLOW=$'\e[33m' RESET=$'\e[0m'
  # Readline prompts need escapes wrapped in \001/\002 so it can measure the prompt width.
  P_CYAN=$'\001\e[36m\002' P_DIM=$'\001\e[2m\002' P_RESET=$'\001\e[0m\002'
else
  BOLD='' DIM='' CYAN='' GREEN='' YELLOW='' RESET='' P_CYAN='' P_DIM='' P_RESET=''
fi

PROJECT='' META='' ANSWERS=''

quit() {
  printf '\n\n%sProgress saved.%s Run Stepwise again to pick up where you left off.\n' "$GREEN" "$RESET"
  exit 0
}
trap quit INT

# --- state ---------------------------------------------------------------

get_state() { sed -n "s/^$1=//p" "$META/state"; }

set_state() {
  local rest
  rest=$(grep -v "^$1=" "$META/state" 2>/dev/null)
  { [[ -n $rest ]] && printf '%s\n' "$rest"; printf '%s=%s\n' "$1" "$2"; } > "$META/state"
}

# --- input ---------------------------------------------------------------

# Reads lines until a blank line. A blank line before any text is ignored, so
# every answer has content. Fails on end of input (Ctrl-D).
read_block() {
  local line text=''
  while :; do
    IFS= read -e -r -p "  ${P_CYAN}>${P_RESET} " line || { [[ -n $text ]] && break; return 1; }
    if [[ -z ${line//[[:space:]]/} ]]; then
      [[ -n $text ]] && break
      continue
    fi
    text+="$line"$'\n'
  done
  printf '%s' "$text"
}

confirm() {
  local reply
  read -e -r -p "  $1 [Y/n] " reply || quit
  [[ -z $reply || $reply == [Yy]* ]]
}


# --- screens -------------------------------------------------------------

header() {
  local stage=$1 title=$2 bar='' i
  for ((i = 1; i <= TOTAL_STAGES; i++)); do
    if ((i < stage)); then bar+="${GREEN}■${RESET}"
    elif ((i == stage)); then bar+="${CYAN}■${RESET}"
    else bar+="${DIM}□${RESET}"; fi
  done
  clear
  printf '%sStepwise%s · %s\n%s  Stage %d of %d\n\n' "$BOLD" "$RESET" "$(get_state name)" "$bar" "$stage" "$TOTAL_STAGES"
  printf '%s%d. %s%s\n\n' "$BOLD" "$stage" "$title" "$RESET"
}

say() { printf '%s\n' "$@" | fold -s -w 78; }

hint() { printf '%s%s%s\n\n' "$DIM" "$1" "$RESET"; }

# --- questions -----------------------------------------------------------

# One question per line, matching the README's Flow section.
questions() {
  case $1 in
    1) cat <<'EOF'
If you could only ship one screen, what would be on that screen?
What's the one thing this app does that nothing else you've used does?
EOF
      ;;
    2) cat <<'EOF'
Which step, if you got it wrong, would break everything after it?
Which steps depend on something you haven't built yet, and which could you start today?
If you had half the time, what would you cut, and what would the app lose?
EOF
      ;;
    3) cat <<'EOF'
For each step, what goes in, what comes out, and what does the app have to remember between runs?
Where does your logic depend on outside input, and what happens when that input is missing or wrong?
Which part of your pseudo-code would be hardest to explain to someone who doesn't know your app?
EOF
      ;;
    4) cat <<'EOF'
Where does this app run, and who needs to open it there?
What does the user see, what handles the logic, and where does the data live? Name one tool for each and say why you chose it.
Which of your choices would be expensive to change in six months? Research those first.
For each library, what problem does it solve that you couldn't solve in a few hundred lines? What does it cost you?
Which part of the system must talk to which other part, and what breaks if one side is slow?
Which choice are you least sure about, and what's the cheapest way to test it before you commit?
EOF
      ;;
  esac
}

stage_title() {
  case $1 in
    1) echo 'Idea' ;;
    2) echo 'Step Breakdown' ;;
    3) echo 'Pseudo Implementation' ;;
    4) echo 'README Part One' ;;
    5) echo 'Syntax Implementation' ;;
    6) echo 'App Execution' ;;
    7) echo 'Test Steps' ;;
    8) echo 'Pseudo Test Implementation' ;;
    9) echo 'Syntax Test Implementation' ;;
    10) echo 'Review and README Part Two' ;;
  esac
}

# Fills the caller's local QS (bash dynamic scoping), so nested calls can't clobber each other.
load_questions() {
  QS=()
  local q
  while IFS= read -r q; do QS+=("$q"); done < <(questions "$1")
}

# Answers are saved one file per question as soon as they're given, so
# quitting mid-stage loses nothing and resuming skips what's answered.
ask_questions() {
  local stage=$1 i f QS
  load_questions "$stage"
  for i in "${!QS[@]}"; do
    f="$ANSWERS/s${stage}q$((i + 1)).txt"
    [[ -s $f ]] && continue
    printf '%s%s%s\n' "$BOLD" "${QS[$i]}" "$RESET"
    read_block > "$f.tmp" || { rm -f "$f.tmp"; quit; }
    mv "$f.tmp" "$f"
    write_notes
    printf '\n'
  done
}

# --- notes.md ------------------------------------------------------------

# notes.md is rebuilt from the saved answers; it's the raw material for the
# app's README in stage 10.
write_notes() {
  local out="$PROJECT/notes.md" stage i f n=0 step QS
  {
    printf '# %s: notes\n\nYour answers from Stepwise, by stage. Stepwise rewrites this file, so keep your own edits elsewhere.\n' "$(get_state name)"
    for ((stage = 1; stage <= LAST_BUILT_STAGE; stage++)); do
      printf '\n## %d. %s\n' "$stage" "$(stage_title "$stage")"
      if ((stage == 1)) && [[ -s $ANSWERS/intent.txt ]]; then
        printf '\n**Intent**\n\n%s' "$(cat "$ANSWERS/intent.txt")"
        printf '\n'
      fi
      if ((stage == 2)) && [[ -s $META/steps.txt ]]; then
        printf '\n**Steps**\n\n'
        n=0
        while IFS= read -r step; do n=$((n + 1)); printf '%d. %s\n' "$n" "$step"; done < "$META/steps.txt"
      fi
      if ((stage == 3)) && [[ -s $META/steps.txt ]]; then
        n=0
        while IFS= read -r step; do
          n=$((n + 1))
          f="$ANSWERS/pseudo$n.txt"
          [[ -s $f ]] && printf '\n**Step %d: %s**\n\n```\n%s```\n' "$n" "$step" "$(cat "$f")"$'\n'
        done < "$META/steps.txt"
      fi
      load_questions "$stage"
      for i in "${!QS[@]}"; do
        f="$ANSWERS/s${stage}q$((i + 1)).txt"
        [[ -s $f ]] && printf '\n**%s**\n\n%s\n' "${QS[$i]}" "$(cat "$f")"
      done
    done
  } > "$out"
}

# --- stages --------------------------------------------------------------

stage_1() {
  header 1 'Idea'
  say "You came here with an app in mind. Pin it down before you build anything."
  printf '\n'
  hint "Answers can be several lines. Press Enter on an empty line to finish one."
  if [[ ! -s $ANSWERS/intent.txt ]]; then
    printf '%sDescribe your app in a sentence or two. Who is it for, and what does it do for them?%s\n' "$BOLD" "$RESET"
    read_block > "$ANSWERS/intent.tmp" || { rm -f "$ANSWERS/intent.tmp"; quit; }
    mv "$ANSWERS/intent.tmp" "$ANSWERS/intent.txt"
    write_notes
    printf '\n'
  fi
  ask_questions 1
}

stage_2() {
  header 2 'Step Breakdown'
  say "Your intent:"
  printf '%s%s%s\n\n' "$DIM" "$(sed 's/^/  /' "$ANSWERS/intent.txt")" "$RESET"
  while [[ ! -s $META/steps.txt ]]; do
    printf '%sBreak it into steps, one per line, in the order you will build them.%s\n' "$BOLD" "$RESET"
    hint "Each step should end in something you can run or see."
    read_block > "$META/steps.tmp" || { rm -f "$META/steps.tmp"; quit; }
    printf '\n'
    nl -w2 -s'. ' "$META/steps.tmp" | sed 's/^/  /'
    printf '\n'
    if confirm 'Are these your steps?'; then
      mv "$META/steps.tmp" "$META/steps.txt"
      write_notes
    else
      rm -f "$META/steps.tmp"
    fi
    printf '\n'
  done
  ask_questions 2
}

stage_3() {
  header 3 'Pseudo Implementation'
  say "For each step, write how it works in plain words: the logic, not the code."
  printf '\n'
  local n=0 step f steps=()
  while IFS= read -r step; do steps+=("$step"); done < "$META/steps.txt"
  for step in "${steps[@]}"; do
    n=$((n + 1))
    f="$ANSWERS/pseudo$n.txt"
    [[ -s $f ]] && continue
    printf '%sStep %d of %d: %s%s\n' "$BOLD" "$n" "${#steps[@]}" "$step" "$RESET"
    read_block > "$f.tmp" || { rm -f "$f.tmp"; quit; }
    mv "$f.tmp" "$f"
    write_notes
    printf '\n'
  done
  printf '%sNow look back over your pseudo-code.%s\n\n' "$BOLD" "$RESET"
  ask_questions 3
}

readme_skeleton() {
  printf '# %s\n\n## What it is\n\n## Steps\n\n## Stack\n\n## Setup\n' "$(get_state name)"
}

stage_4() {
  header 4 'README Part One'
  say "Before any code, decide what you're building it with: where it runs, frontend, backend, data, libraries and tools. Research the choices you're unsure of."
  printf '\n'
  ask_questions 4

  local readme="$PROJECT/README.md"
  if [[ ! -e $readme ]]; then
    readme_skeleton > "$readme"
    set_state readme_sum "$(cksum < "$readme")"
  fi
  printf '%sNow write Part One of your README.%s\n' "$BOLD" "$RESET"
  say "Open README.md in your editor and fill in each section in your own words. Your answers so far are in notes.md."
  printf '\n  %s\n  %s\n\n' "$readme" "$PROJECT/notes.md"
  command -v code > /dev/null && code "$readme" "$PROJECT/notes.md" 2> /dev/null
  while :; do
    read -e -r -p "  ${P_DIM}Save the file, then press Enter.${P_RESET}" _ || quit
    [[ $(cksum < "$readme") != "$(get_state readme_sum)" ]] && break
    printf '  %sREADME.md hasn'\''t changed yet. Save your edits first.%s\n' "$YELLOW" "$RESET"
  done
}

finish() {
  header "$((LAST_BUILT_STAGE + 1))" "$(stage_title $((LAST_BUILT_STAGE + 1)))"
  say "Stages 1 to $LAST_BUILT_STAGE are done. You have a plan, pseudo-code and a stack, all in your own words."
  printf '\n'
  say "Stage $((LAST_BUILT_STAGE + 1)) isn't in Stepwise yet. Your files are here:"
  printf '\n  %s\n\n' "$PROJECT"
}

# --- project -------------------------------------------------------------

slugify() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//; s/-*$//'; }

open_project() {
  local dir name
  if (($# > 0)); then
    dir=$1
  elif [[ -f .stepwise/state ]]; then
    dir=.
  else
    clear
    printf '%sStepwise%s\n\n' "$BOLD" "$RESET"
    say "Stepwise asks the questions. You do the thinking and write every line."
    printf '\n'
    while [[ -z ${name:-} ]]; do
      read -e -r -p "  What's your app called? " name || exit 0
    done
    dir=$(slugify "$name")
    [[ -z $dir ]] && dir=app
  fi

  mkdir -p "$dir/.stepwise/answers" || exit 1
  PROJECT=$(cd "$dir" && pwd)
  META="$PROJECT/.stepwise"
  ANSWERS="$META/answers"
  if [[ ! -f $META/state ]]; then
    : > "$META/state"
    set_state name "${name:-$(basename "$PROJECT")}"
    set_state stage 1
  fi
}

main() {
  open_project "$@"
  local stage
  while :; do
    stage=$(get_state stage)
    ((stage > LAST_BUILT_STAGE)) && break
    "stage_$stage"
    set_state stage $((stage + 1))
  done
  finish
}

main "$@"
