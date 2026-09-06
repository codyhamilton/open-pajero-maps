"""Check plug-in modules: each exposes a module-level `CHECKS` list of
`harness.context.Check` instances. `harness.registry.discover()` collects
them from every module here, in module-name order."""
