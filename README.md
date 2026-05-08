# MGT470 Business Decoupling Analyst

Local-first AI workflow for Teixeira-style business model, decoupling, and investment analysis.

The project is designed to take incomplete company information such as a company name, website, pitch deck, memo, filing, or notes, then produce a reproducible analysis pipeline:

```text
raw input
  -> research brief
  -> normalized company profile
  -> customer value chain
  -> value type diagnosis
  -> weak link analysis
  -> decoupling strategy
  -> business model judgment
  -> professional Markdown report
```

The first version targets a CLI plus Markdown output, not a web app. The final report is intended to be readable in Obsidian and GitHub.

See [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for the full architecture.
