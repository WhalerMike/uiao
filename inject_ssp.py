import pathlib, sys

APP = pathlib.Path('src/uiao_core/cli/app.py')
text = APP.read_text(encoding='utf-8').replace('\r\n', '\n')

u = chr(95) * 2
NEW_COMMAND = (
    '\n@app.command()\n'
    'def ir_ssp_report(\n'
    '    normalized_json: str = typer.Argument(..., help=\'Path to normalized SCuBA JSON file.\'),\n'
    '    fmt: str = typer.Option(\'markdown\', \'--format\', \'-f\', help=\'Output format: markdown | json\'),\n'
    '    out: str = typer.Option(\'\', \'--out\', \'-o\', help=\'Write output to file.\'),\n'
    ') -> None:\n'
    '    \'\'\'Generate SSP narrative + lineage from SCuBA -> IR -> Evidence -> Governance.\'\'\'\n'
    '    import json as _json\n'
    '    from pathlib import Path as _Path\n'
    '    from uiao_core.evidence.bundle import build_bundle_from_transform_result\n'
    '    from uiao_core.governance.actions import build_governance_actions\n'
    '    from uiao_core.coverage.coverage import build_coverage_links\n'
    '    from uiao_core.ssp.narrative import build_control_narratives, format_ssp_markdown\n'
    '    from uiao_core.ssp.lineage import build_lineage_index\n'
    '    from uiao_core.ir.adapters.scuba.transformer import transform_scuba_to_ir\n'
    '    result = transform_scuba_to_ir(normalized_json)\n'
    '    bundle = build_bundle_from_transform_result(result)\n'
    '    actions = build_governance_actions(bundle.evidence, bundle.drift_states)\n'
    '    links = build_coverage_links(bundle.evidence)\n'
    '    narratives = build_control_narratives(links, actions)\n'
    '    if fmt.lower() == \'json\':\n'
    '        lineage = build_lineage_index(links, actions)\n'
    '        output_text = _json.dumps(lineage, indent=2)\n'
    '    else:\n'
    '        output_text = format_ssp_markdown(narratives)\n'
    '    typer.echo(output_text)\n'
    '    if out:\n'
    '        _Path(out).parent.mkdir(parents=True, exist_ok=True)\n'
    '        _Path(out).write_text(output_text, encoding=\'utf-8\')\n'
    '        console.print(\'[green]SSP report written to \' + out + \'[/green]\')\n'
    '\n'
)
M1 = 'if ' + u + 'name' + u + ' == ' + chr(34) + u + 'main' + u + chr(34) + ':'
M2 = 'if ' + u + 'name' + u + chr(32) + chr(61) + chr(61) + chr(32) + chr(39) + u + 'main' + u + chr(39) + ':'
MARKER = M1 if M1 in text else M2
if MARKER not in text:
    print('ERROR: marker not found', file=sys.stderr)
    sys.exit(1)
new_text = text.replace(MARKER, NEW_COMMAND + MARKER)
APP.write_text(new_text, encoding='utf-8')
print('OK lines=' + str(len(new_text.splitlines())))
