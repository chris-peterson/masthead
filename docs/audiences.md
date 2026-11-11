# Who the hub is for

A repo's documentation has three audiences:

| Audience | Who | Where their docs live |
| --- | --- | --- |
| End users | people using what the repo ships | the documentation hub: a pages site or wiki |
| Maintainers | people changing the repo | `README.md`, `CONTRIBUTING.md` |
| Agents | AI tools working in the repo | `AGENTS.md`, `CLAUDE.md`, rules, skills |

masthead writes for end users. Everything it puts in the hub is for them, and it
turns away content that isn't.

The test is one question: **could someone who only uses what this repo ships,
with no checkout, act on this?** If they couldn't, the content belongs to
maintainers or agents, and masthead says so instead of publishing it.

## What stays out of the hub

| The content | Why it's turned away | Audience |
| --- | --- | --- |
| Build, test, or release steps; repo layout; CI internals; dev setup | Only someone with a checkout can use it | maintainers |
| Conventions and always/never rules an AI tool follows when changing the code | It's instructions for the agent doing the work | agents |
| A page that only makes sense with links into the source | A hub reader has no checkout to follow them into | maintainers, or rewrite it to stand alone |

Everything else is hub material: what the project is, why you'd use it, how to
install and configure it, worked examples, and the hazards: what surprises
people, what fails quietly, what to check before you rely on it.

## Handing content to the right place

[cleat](https://chris-peterson.github.io/cleat/) routes documentation among all
three audiences. When masthead turns content away, it announces which audience
the content belongs to, and a session that has cleat installed can pick it up.
When cleat finds content meant for end users, it can do the same in the other
direction. Neither plugin moves the other's content on its own: each one tells
the agent, and the agent decides where the content goes.

The announcements themselves are listed on the [Events](/events) page.
