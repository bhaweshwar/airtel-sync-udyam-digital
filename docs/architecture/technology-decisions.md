# Technology decisions

Date checked: 2026-11-04. Versions are pinned in project manifests/wrapper; recheck official compatibility before upgrades.

| Area | Selection | Rationale / status |
|---|---|---|
| Java target | Java 21 bytecode (`maven.compiler.release=21`) | LTS deployment baseline and ecosystem breadth. Current machine has JDK 25 only; JDK 25 can compile with `--release 21` and execute Java 21 bytecode. |
| Spring Boot | 3.5.16 | Stable 3.5 line; official system requirements say Java 17 minimum and compatible through Java 25. Keeping Boot 3.x avoids a major framework transition during foundation work. |
| Maven | Apache Maven 3.9.11 via Maven Wrapper 3.3.4 | Reproducible Maven version without global installation. Wrapper distribution is downloaded on first use; wrapper files are committed except generated wrapper JAR. |
| Frontend runtime | Node 24.18 / npm 11.16 in current workspace | Installed versions; Vite 8 requires Node 20.19+ or 22.12+, so Node 24 meets its requirement. Recommend an even-numbered LTS runtime. |
| React | 19.3.0 | Stable official React release as of this document date. |
| Vite | 8.3.0; `@vitejs/plugin-react` 6.2.1 | Vite 8 stable line and official React plugin; plugin 6 targets Vite 8. |
| TypeScript | 6.0.2 | Stable transition version, preferring ecosystem maturity while TypeScript 7.0 is newly released. Strict mode enabled. |
| Backend API | Spring MVC REST | Simple synchronous API fits the prototype and modular monolith. |
| Persistence | SQLite, planned; not yet connected | Lightweight local prototype store. Keep behind repository boundary; not a production HA database decision. |
| OCR | Tesseract, planned; not yet integrated | Existing local install is available; Java adapter and privacy controls are future work. |
| LLM | Provider interface, planned; no provider selected | Deterministic rules remain authoritative; minimize data and support deterministic fallback. |

## Java 25 compatibility choice

Spring Boot 3.5.16 officially supports Java 25, so the installed JDK is technically compatible. The project nevertheless targets Java 21 bytecode because it is a widely deployed LTS baseline and limits runtime requirements for contributors/deployment. The current Java 25 compiler is expected to support `--release 21`; builds verify this. Java 21 is not installed in the current workspace. This is an explicit baseline/runtime distinction, not a claim that Spring Boot requires Java 21.

## References

- [Spring Boot 3.5.16 system requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html)
- [React versions](https://react.dev/versions) and [React 19.3 release](https://react.dev/blog/2026/09/09/react-19-3)
- [Vite 8 announcement and Node requirements](https://vite.dev/blog/announcing-vite8)
- [Vite release policy](https://vite.dev/releases)
- [Apache Maven Wrapper documentation](https://maven.apache.org/tools/wrapper/)
- [Maven Wrapper releases](https://github.com/apache/maven-wrapper/releases)
- [TypeScript 6.0 notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html)
