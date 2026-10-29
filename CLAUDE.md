## Guiding principles
Keep it simple. Write the minimal, readable code that solves the problem. Clarity beats cleverness.
Write for humans. A developer new to the codebase should understand the code without explanation. Use clear names and straightforward control flow.
Use libraries, don't reinvent. Prefer a well-established, actively maintained library over writing long custom logic for a solved problem (e.g. parsing, validation, date handling, HTTP, retries).
Stay current. Use modern Python syntax and features (e.g. match, X | Y type unions, dataclasses) and actively maintained, up-to-date libraries. Avoid deprecated APIs.
Ask before adding complexity. If a requirement seems to need complex logic, stop and discuss it first: explain why, propose simpler alternatives, and confirm before implementing.
Use domain knowledge. Draw on knowledge of the project's domain and check current documentation for libraries and tools when unsure, rather than guessing.
Follow best practices. Apply established conventions for Python and for this project's domain.