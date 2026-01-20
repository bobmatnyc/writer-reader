# Chapter 2: Core Concepts

Understanding the core concepts is essential.



## Book Structure

A book consists of:

- **Chapters**: Individual markdown files
- **Sections**: Headings within chapters
- **Notes**: Annotations for review

<!-- NOTE: 2026-01-19T22:51:59 - Section structure looks good -->


## Working with Chapters

Chapters are numbered markdown files in the `src/` directory.

### File Naming

Use consistent naming like:
- `chapter-01.md`
- `chapter-02.md`

### Chapter Metadata

Each chapter can have YAML frontmatter:

```yaml
---
title: My Chapter
draft: false
---
```



## Working with Sections

Sections are defined by `##` headings.

Each section can be:
- Read individually
- Updated without affecting other sections
- Annotated with notes



## The Note System

Notes are HTML comments with timestamps:

```html
<!-- NOTE: 2024-01-19T15:30:00 - Your note here -->
```

They're invisible in rendered output but visible to Claude.
