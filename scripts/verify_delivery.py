"""Перед сборкой мы проверяем сохранённые результаты и комплект файлов без обращения к сети."""
from pathlib import Path
import json,re,hashlib


def main():
    root=Path(__file__).resolve().parent.parent
    read=lambda name:json.loads((root/'artifacts'/name).read_text(encoding='utf-8'))
    agents=read('agent_eval.json');raw=read('llm_eval_raw.json');api=read('api_smoke.json');sandbox=read('sandbox_evidence.json')
    qa=json.loads((root/'output/pdf/qa.json').read_text())
    tests=(root/'artifacts/test-results.txt').read_text()
    observations=[json.loads(x) for x in (root/'artifacts/continuous_monitor.jsonl').read_text().splitlines()]
    checks={
      'full_test_suite':bool(re.search(r'30 passed',tests)) and 'failed' not in tests,
      'five_agent_scenarios':len(agents)==5 and all(a['passed'] for a in agents),
      'independent_validator':all(a['result']['validator_model']=='gemma3:4b' for a in agents if a['result']['status']=='ok'),
      'real_model_probes':len(raw)==40 and len({r['model'] for r in raw})==5 and all(r['error'] is None for r in raw),
      'six_recommenders_evaluated':len(read('recsys_results.json')['test'])==6,
      'api_health':api['health']['status']=='ready' and api['health']['neural_loaded'],
      'http_agent_and_trajectory':api.get('agent',{}).get('status')=='ok' and api.get('trace_events',0)>10,
      'sandbox_probes':len(sandbox['checks'])==8 and all(sandbox['checks'].values()),
      'continuous_monitor':sum(r['name']=='monitor.health' and r.get('status')=='ready' for r in observations)>=2,
      'eight_diagrams':len(list((root/'docs/diagrams').glob('*.png')))==8 and len(list((root/'docs/diagrams').glob('*.svg')))==8,
      'pdf_rendered':qa['pages']>=10 and not qa['out_of_page_text'] and not qa['text_replacement_glyph'],
      'trained_checkpoint':(root/'artifacts/two_tower.pt').stat().st_size>10000}
    files=[]
    for pattern in ['cineagents/*.py','scripts/*.py','scripts/*.sh','deploy/*.sh','prompts/*.md','agent_context/*.md','agent_skills/*/SKILL.md']:
        files.extend(root.glob(pattern))
    manifest={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    (root/'artifacts/source_manifest.json').write_text(json.dumps(manifest,indent=2))
    result={'checks':checks,'all_local_checks_passed':all(checks.values()),'remote_publication':'not published; add the repository URL before submission','report_sha256':hashlib.sha256((root/'output/pdf/CineAgents_отчет.pdf').read_bytes()).hexdigest()}
    (root/'artifacts/acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    if not result['all_local_checks_passed']:raise SystemExit(1)

if __name__=='__main__':main()
