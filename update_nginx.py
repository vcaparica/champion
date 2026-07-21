"""Update nginx config with Champion blocks."""
config_path = "/etc/nginx/sites-enabled/cegoemtiroteio.com.br"

with open(config_path) as f:
    config = f.read()

# Remove old champion block
old_start = "    # CHAMPION GAME SERVER"
old_end = "    # DEFAULT"
start_idx = config.find(old_start)
end_idx = config.find(old_end, start_idx)
if start_idx >= 0 and end_idx >= 0:
    config = config[:start_idx] + config[end_idx:]

# Insert new champion block
with open("/tmp/nginx-champion.conf") as f:
    champion_block = f.read()

insert_before = "    # DEFAULT"
config = config.replace(insert_before, champion_block + insert_before, 1)

with open(config_path, "w") as f:
    f.write(config)
print("config_updated")
