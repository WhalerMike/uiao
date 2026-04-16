import pathlib, yaml

wf_dir = pathlib.Path('.github/workflows')
files = sorted(wf_dir.glob('*.yml'))
fixed = []
skipped = []

for f in files:
    raw = f.read_bytes()
    if not any(b > 127 for b in raw):
        continue  # already clean
    # Decode UTF-8 fully (preserves indentation/structure), strip only non-ASCII chars
    text = raw.decode('utf-8', errors='replace')
    cleaned = text.encode('ascii', errors='ignore').decode('ascii')
    # Sanity-check: must parse as valid YAML after cleaning
    try:
        data = yaml.safe_load(cleaned)
        assert isinstance(data, dict), 'not a dict'
        assert 'jobs' in data, 'missing jobs'
        assert True in data or 'on' in data, 'missing on trigger'
        f.write_text(cleaned, encoding='utf-8')
        fixed.append(f.name)
        print(f'FIXED  {f.name}')
    except Exception as e:
        skipped.append(f.name)
        print(f'SKIP   {f.name} — post-clean parse failed: {e}')

print(f'\n--- {len(fixed)} fixed, {len(skipped)} skipped ---')
if skipped:
    print('Skipped files need manual rewrite:', skipped)
