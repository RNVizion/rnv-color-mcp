unset GITHUB_TOKEN GH_TOKEN
gh auth login -h github.com -p https -s repo -w
bash open_pr.sh
