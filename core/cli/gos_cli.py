import argparse
import json

from core.providers.provider_framework import ProviderFramework
from core.pipeline.governance_pipeline import GovernancePipeline
from core.providers.provider_registry import ProviderRegistry
from core.governance.audit_log import AuditLog


def main():
    parser = argparse.ArgumentParser(prog="gos")
        sub = parser.add_subparsers(dest="command")

            sub.add_parser("providers")
                sub.add_parser("providers-health")
                    sub.add_parser("audit")

                        run_cmd = sub.add_parser("run")
                            run_cmd.add_argument("--provider", default="demo")

                                detect_cmd = sub.add_parser("detect")
                                    detect_cmd.add_argument("--provider", default="demo")

                                        args = parser.parse_args()
                                            framework = ProviderFramework()

                                                if args.command == "providers":
                                                        print(json.dumps(
                                                                    {k: v.dict() for k, v in framework.metadata().items()},
                                                                                indent=2
                                                                                        ))
                                                                                                return

                                                                                                    if args.command == "providers-health":
                                                                                                            print(json.dumps(
                                                                                                                        {k: v.dict() for k, v in framework.health().items()},
                                                                                                                                    indent=2
                                                                                                                                            ))
                                                                                                                                                    return

                                                                                                                                                        if args.command == "audit":
                                                                                                                                                                log = AuditLog()
                                                                                                                                                                        with open(log.path, "r", encoding="utf-8") as f:
                                                                                                                                                                                    for line in f:
                                                                                                                                                                                                    print(line.strip())
                                                                                                                                                                                                            return

                                                                                                                                                                                                                if args.command == "detect":
                                                                                                                                                                                                                        registry = ProviderRegistry()
                                                                                                                                                                                                                                adapter_cls = registry.get(args.provider)
                                                                                                                                                                                                                                        adapter = adapter_cls()
                                                                                                                                                                                                                                                pipeline = GovernancePipeline(adapter)
                                                                                                                                                                                                                                                        result = pipeline.detect_only()
                                                                                                                                                                                                                                                                print(json.dumps(result, indent=2))
                                                                                                                                                                                                                                                                        return

                                                                                                                                                                                                                                                                            if args.command == "run":
                                                                                                                                                                                                                                                                                    registry = ProviderRegistry()
                                                                                                                                                                                                                                                                                            adapter_cls = registry.get(args.provider)
                                                                                                                                                                                                                                                                                                    adapter = adapter_cls()
                                                                                                                                                                                                                                                                                                            pipeline = GovernancePipeline(adapter)
                                                                                                                                                                                                                                                                                                                    result = pipeline.run()
                                                                                                                                                                                                                                                                                                                            print(json.dumps(result, indent=2))
                                                                                                                                                                                                                                                                                                                                    return

                                                                                                                                                                                                                                                                                                                                        parser.print_help()


                                                                                                                                                                                                                                                                                                                                        if __name__ == "__main__":
                                                                                                                                                                                                                                                                                                                                            main()
                                                                                                                                                                                                                                                                                                                                            