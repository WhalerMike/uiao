# Update set — `x_fed_compliance`

Assemble in a sub-prod instance and export as one importable XML
(`x_fed_compliance-update-set.xml`), exactly as the day-2 app does:

1. Create the scoped app `x_fed_compliance`; set properties `mid_server`,
   `boundary` (fixed `gcc-moderate`), `test_mode` (default `false`).
2. Import the three Script Includes; create the two REST messages per
   `rest/README.md` with tenant credential aliases.
3. Build the three Flows per `flow/flow-blueprint.md`; load
   `data/control-map.json` as app data.
4. Build + run the ATF suite per `atf/README.md` (test_mode on).
5. Export the update set; ship the XML here.

The XML is deliberately not committed from prose — committing an unbuilt,
untested update set would be worse than none (same disposition as the DDI app
skeleton).
