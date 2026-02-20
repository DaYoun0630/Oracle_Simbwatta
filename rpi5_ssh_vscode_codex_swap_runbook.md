# RPi 5 Runbook: Keep SSH/VSCode/Codex Stable During Heavy Preprocessing

Target machine:
- Raspberry Pi 5
- ARM64
- 8GB RAM
- SSD available for swap

Goal:
- Reduce OOM kills and session drops while heavy preprocessing runs
- Keep enough headroom for at least 3 connected users

## 0) Check Current Status
Run on the Raspberry Pi (SSH terminal):

```bash
swapon --show --output=NAME,TYPE,SIZE,USED,PRIO
free -h
zramctl || true
```

## 1) Increase SSD Swap to 16GB
Assume SSD swapfile path is `/mnt/ssd/swapfile`.
If your path is different, replace it in all commands.

```bash
sudo swapoff /mnt/ssd/swapfile 2>/dev/null || true
sudo fallocate -l 16G /mnt/ssd/swapfile
sudo chmod 600 /mnt/ssd/swapfile
sudo mkswap /mnt/ssd/swapfile
sudo swapon /mnt/ssd/swapfile
```

Persist with lower priority than zram:

```bash
sudo cp /etc/fstab /etc/fstab.bak.$(date +%F-%H%M%S)
sudo sed -i '\#^/mnt/ssd/swapfile[[:space:]]#d' /etc/fstab
echo '/mnt/ssd/swapfile none swap defaults,pri=10 0 0' | sudo tee -a /etc/fstab
```

## 2) Configure zram as First Swap Tier
Install and configure `zram-tools`:

```bash
sudo apt update
sudo apt install -y zram-tools
```

Edit `/etc/default/zramswap`:

```ini
ALGO=lz4
PERCENT=50
PRIORITY=100
```

Apply:

```bash
sudo systemctl enable zramswap
sudo systemctl restart zramswap
```

## 3) Kernel Swap Tuning
Set balanced values for responsiveness + stability:

```bash
sudo tee /etc/sysctl.d/99-swap-tuning.conf >/dev/null <<'EOF'
vm.swappiness=40
vm.page-cluster=0
EOF
sudo sysctl --system
```

## 4) Verify Priority Order
Expected:
- `/dev/zram0` has higher `PRIO` (e.g. 100)
- SSD swapfile has lower `PRIO` (e.g. 10)

```bash
swapon --show --output=NAME,TYPE,SIZE,USED,PRIO
```

## 5) Run Heavy Preprocessing With Resource Guardrails
This prevents one job from starving SSH/VSCode users.
Replace `YOUR_COMMAND_HERE` with your actual preprocess command.

```bash
systemd-run --scope \
  -p MemoryMax=5500M \
  -p CPUQuota=300% \
  bash -lc 'nice -n 10 ionice -c2 -n7 YOUR_COMMAND_HERE'
```

Example:

```bash
systemd-run --scope \
  -p MemoryMax=5500M \
  -p CPUQuota=300% \
  bash -lc 'nice -n 10 ionice -c2 -n7 uv run python src/gpt/main.py --zip_path ./data/image/7team_MRI_3DT1w_Final_dataset.zip --output_dir ./data --labels_csv ./data/labels.csv --skull_strip_method synthstrip'
```

## 6) Real-Time Monitoring
Use a second SSH window:

```bash
vmstat 1
```

Healthy signs:
- `si`/`so` mostly near 0
- system remains responsive

Warning signs:
- sustained nonzero `si`/`so` for long periods
- laggy shell + delayed SSH response

If warning signs persist:
- lower preprocessing concurrency/workers to `1-2`
- reduce batch size
- lower `MemoryMax` slightly (to protect interactive users more)

## 7) Fast Troubleshooting
Check if OOM killer was triggered:

```bash
dmesg -T | rg -i 'out of memory|oom|killed process'
```

If OOM still occurs:
- increase SSD swap further (for safety net)
- keep zram enabled
- reduce parallel workload

## 8) Practical Defaults for Your Case
- zram: `PERCENT=50`, `PRIORITY=100`
- SSD swap: `16G`, `pri=10`
- `vm.swappiness=40`
- preprocessing workers: `1-2`
- run heavy jobs inside `tmux` for safer long sessions
