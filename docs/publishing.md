# Publishing this to GitHub

Two routes. Both assume an Ubuntu terminal (native or WSL) and both end with the
same thing: this repo pushed to GitHub with its history intact.

If you are in WSL, your Windows drive is under `/mnt/c/`, so the project is at
something like `/mnt/c/Users/aleks/Documents/KiCad/LED Butterfly PCB/butterfly-pcb`.

## Once, if you have never set git up on this machine

```bash
git config --global user.name  "Aleksander Norman"
git config --global user.email "aleksanderjnorman@gmail.com"
git config --global init.defaultBranch main
```

## Starting from the zip

```bash
cd ~/Downloads
unzip -o butterfly-pcb.zip
cd butterfly-pcb
git log --oneline          # the history is already in here
```

## Route A — create the repo in the browser, push from the terminal

1. Go to <https://github.com/new>
2. Repository name: `twinkling-butterfly`
3. Leave **"Add a README file", ".gitignore" and "license" all unchecked** — the
   repo must start empty or the push below is rejected.
4. Create repository, then in the terminal:

```bash
cd ~/Downloads/butterfly-pcb
git remote add origin https://github.com/YOUR-USERNAME/twinkling-butterfly.git
git branch -M main
git push -u origin main
```

GitHub will ask for a username and password. The password is **not** your account
password — it is a personal access token from
<https://github.com/settings/tokens> with the `repo` scope. To avoid retyping it:

```bash
git config --global credential.helper store
```

## Route B — do the whole thing from the terminal with the GitHub CLI

```bash
sudo apt update && sudo apt install -y gh
gh auth login          # choose GitHub.com, HTTPS, then "Login with a web browser"

cd ~/Downloads/butterfly-pcb
gh repo create twinkling-butterfly --public --source=. --remote=origin --push
```

Swap `--public` for `--private` if you would rather keep it to yourself. `gh` can
flip it later with `gh repo edit --visibility public`.

## Afterwards

```bash
git add -A
git commit -m "Route the hindwing pixel chain"
git push
```

The CI workflow in `.github/workflows/check.yml` runs on every push: it reruns the
netlist checker, rebuilds the BOM and regenerates the outline, then fails if any of
them come out different from what is committed. So if you edit a sheet by hand in
KiCad, either rerun the generators or expect that check to tell you the committed
outputs are stale.
