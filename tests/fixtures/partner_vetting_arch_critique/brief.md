## 📝 Partner Vetting — Product Context Document

**Purpose:** This document is a faithful, exhaustive capture of everything discussed in a product discovery conversation with the product owner of Partner Vetting. It is raw material for architectural reasoning — not a solution document, not a set of decisions, and not a specification. Ideas are expressed with the same level of certainty as they were originally expressed. Where the product owner indicated uncertainty, offered a suggestion, or left something open, this document reflects that faithfully. Nothing is presented as settled unless it was explicitly stated as settled.
---
## 1. Origin and Context
Partner Vetting did not emerge from scratch. It grew out of an existing internal tool called Vera, which was built to address a specific and immediate problem inside one of the company's products — a logistics marketplace platform referred to throughout as Marketplace.
Marketplace is a two-sided platform where shippers and carriers come together to agree on transport loads. Shippers operate in two modes. The first is contracted lanes: steady, recurring transport needs where a shipper — say, a large manufacturer — knows their volumes and routes in advance, runs procurement exercises, and locks in carriers over a period of time. Those carriers then run those lanes repeatedly as agreed. The second mode is spot freight: urgent, unplanned transport needs where the shipper posts a load on the platform — for example, a full truckload from Berlin to Barcelona at short notice — and carriers bid on it. The shipper then picks from among the bids, often on price, but sometimes on other factors.
The spot freight scenario creates a trust problem. A shipper who chooses a carrier they have never worked with before is taking a risk. The carrier might arrive without proper insurance. They might not be a legitimately registered company. They might not hold the necessary licenses to operate in the relevant countries. In extreme cases, they might not be trustworthy at all. There was, before Vera, no reliable mechanism to verify any of this.
Vera was created to address this problem, at least partially. The team behind Vera, through an iterative process of testing prompts and approaches, built a flow where carriers upload a small set of documents proving they hold certain credentials. Vera then validates those credentials — not by trusting the documents alone, but by cross-referencing with external sources such as government websites or authoritative third-party APIs. The four things Vera checks today are: VAT registration, company registration, cargo insurance validity, and EU transport license. When those four things are verified, Vera can signal to users of Marketplace that at minimum these four things are confirmed for a given carrier.
Vera works, to a degree. Trimble as a company has over 200,000 carriers in its network across all its products. Within Marketplace specifically, approximately 35,000 carriers are active. Of those, only around 6% have been vetted through Vera. The process remains largely manual, is used only for internal purposes, and is not visible to or configurable by customers. There is no customer-facing interface. Customers cannot see what was vetted, cannot configure additional vetting criteria, and cannot act on the vetting information directly within their workflows.
Beyond the low adoption rate and manual nature of the process, Vera has additional structural limitations. Vetting rules differ by country. Each of the four checks Vera performs may need to be validated against different sources depending on the carrier's country of origin, the countries through which transport passes, and the regulatory regimes in play. Europe is particularly complex in this regard: EU-level regulations coexist with national laws, and there are adjacent non-EU countries — Switzerland and others — that carriers may operate through. A large carrier such as Duvenbeck or Ekol Walter might have operations across the entirety of Europe, with different divisions holding credentials for different country combinations. Vera's current handling of this country-level complexity exists but is not clean, not productized, not well-documented, and not flexible enough to expand — even for internal use.
The decision was made to build something new: a product that takes what Vera proved was possible and rebuilds it with a fundamentally different scope, ambition, and architecture. That product is Partner Vetting.
---
## 2. The Problem Being Solved
The problems that Partner Vetting is intended to address operate at several levels simultaneously.
At the most immediate level, there is the trust deficit in spot freight. When a shipper and a carrier engage for the first time — particularly on a platform like Marketplace — the shipper has no reliable way to know that the carrier is who they say they are, that their insurance is valid, that they hold the right licenses, or that they are capable of executing the specific type of transport being requested. The current situation relies either on the carrier's self-declaration or on a manual vetting process that reaches only 6% of the active carrier pool. This is not an acceptable state for a logistics software provider operating at scale.
At a deeper level, there is regulatory complexity. The EU Deforestation Regulation (EUDR) requires large and medium operators to comply by December 30, 2026. Non-compliance carries fines of up to 4% of total annual EU turnover. The Corporate Sustainability Due Diligence Directive (CSDDD) and the German Supply Chain Due Diligence Act (LkSG) mandate that companies identify and mitigate human rights and environmental risks across their entire supply chains — not just with direct suppliers. These are not theoretical future requirements; they are active regulatory drivers that logistics operators are already working to address.
In North America, the dominant drivers are different but equally urgent. Cargo theft rose 16% in 2025, and the increase is not primarily in opportunistic theft but in what is called strategic theft — fictitious pickups, identity theft, double brokering — which has increased by approximately 1,500% since 2022. Jury awards in liability cases involving carriers — so-called nuclear verdicts — reached a record median of \$51 million in 2024. Insurance premiums have risen 36–38% over the past decade as a result. Traditional compliance tracking, which relies on static document snapshots, typically achieves only 65–75% compliance rates because policies can be cancelled hours after a valid-looking document is submitted.
There is also a geographic and operational complexity problem. Carriers operating across Europe may need to be vetted differently depending on which countries they operate in, which routes they run, and what goods they carry. A carrier valid for general freight from France to Spain may need additional validation before running lanes from Poland to Ireland that cross through the UK. The configuration required to manage this — different checks, different sources, different validity windows, different document types — is currently not handled in any systematic way.
Finally, there is a commercial problem. The vetting infrastructure that exists today is internal and hidden. Customers who buy Trimble's products cannot see it, cannot build on it, and cannot extend it for their own purposes. This is a missed opportunity both commercially and strategically, given the size of the carrier network Trimble already has.
---
## 3. The Market and Competitive Landscape
The competitive landscape for carrier and partner vetting is bifurcated between legacy document repository tools and newer identity or agent-driven platforms.
RMIS is the established first-generation standard. It is a static document repository — it stores certificates of insurance, authority documents, W-9s, and similar paperwork. It has a large customer base but is fundamentally limited by its snapshot-in-time nature. It cannot detect mid-term policy cancellations or fraudulent credentials. Its compliance ceiling is estimated at 65–75%.
Highway has built what it calls a Carrier Identity platform. It performs real-time entity verification using ELD data, fleet data, and a combination of public and private sources. It has created a two-sided trust network through a product called Highway for Carriers, which allows carriers to verify brokers — not just the other way around. This two-way model is notable because it gives carriers a reason to participate. Highway's gaps are significant for the intended market: it has no European presence, no logistics-specific operational signal such as lane history or cargo fitness data, and it is primarily an identity verification tool rather than a full vetting workflow platform.
Certificial has built what it calls a Smart COI — a live connection between a certificate of insurance requestor and the insurance agent's management system. This eliminates forged certificates and pushes compliance rates above 90% for insurance specifically. Its limitation is that it is insurance-only. It does not address carrier identity, regulatory compliance, or agentic orchestration of any kind.
Hwy Haul, operating under the Miles brand, is the most advanced agentic realization in the space. It deploys multiple specialized AI agents per task — vetting, fraud prevention, negotiation — and claims 20–50% gross margin gains with significant reductions in manual touchpoints per load. It is US-focused, optimized for its own brokerage operations rather than offered as a vetting-as-a-service product, and has no European regulatory coverage.
The gap that Partner Vetting is positioned to fill is the combination of a large pre-existing carrier network with agentic capabilities and European regulatory depth. No existing competitor has all three. Trimble's carrier network — over 200,000 carriers — is the cornered resource that competitors cannot replicate without becoming logistics platforms themselves.
---
## 4. The Vision for Partner Vetting
Partner Vetting is intended to be a vetting-as-a-service capability that is initially built for carriers in the logistics domain but designed from the ground up to be extensible to any type of partner in any industry.
The decision to call it Partner Vetting rather than Carrier Vetting is deliberate and reflects an architectural intention. The product is being designed so that the vetting mechanisms it provides are not specific to carriers or to logistics. A construction company vetting material suppliers, a forestry operator vetting wood mill companies, an agricultural business vetting contractors — all of these should, if the product is built correctly, be expressible using the same underlying system. Carriers in logistics are the starting point because that is where the problem is clearest, where Trimble already has network density, and where the regulatory pressure is most immediate. But the naming and the intended architecture reflect the broader ambition.
The product is not conceived of purely as a standalone application. It is conceived of as a skill within a broader AI agent called ARC. ARC is described as an omnipotent agent — an AI interface, presented in the form of a typical chat UI similar to ChatGPT or similar products, that orchestrates a catalog of skills to complete tasks on behalf of users. A user might open ARC as a side panel within a Trimble product, ask it to perform a task, and ARC would pull from its skill catalog to do so. Examples of other skills might include data entry, negotiation assistance, or load management. Partner Vetting would be one skill in this catalog.
The product owner was clear that "Partner Vetting" as a commercially offered skill is an umbrella. Underneath it, there would be many sub-skills — specific capabilities called when vetting is being configured, when validation is being executed, when results are being presented. These sub-skills would not be individually sold or named externally. Commercially, the offering is Partner Vetting. Internally, it is a collection of more granular capabilities.
The relationship to ARC also has a technical dimension. The way ARC consumes skills is through a mechanism called MCP (Model Context Protocol). The intention is that Partner Vetting would expose itself as an MCP server, and ARC would call it through that interface. This is discussed further in the section on consumption surfaces.
---
## 5. The People Who Will Use It
The product owner described several distinct categories of people who would interact with Partner Vetting. These are not yet formally named roles — naming is something still to be established — but the distinctions between them are clear and important.
**Internal Trimble administrators** are people inside Trimble who manage products and customers. They would log in with internal Trimble credentials and have the ability to configure vetting setups for specific products — for example, configuring how carriers should be vetted when using Marketplace, or when using a transport management system product. They would also potentially configure defaults that apply across all products or for specific customers being onboarded. These users have the broadest permissions and are responsible for setting up the underlying capabilities that others then use.
**Customer administrators** are users who belong to a company that has purchased a Trimble product and has Partner Vetting enabled for that product. A large shipper, for example, might have an administrator who can log in and configure vetting workflows specific to their organisation — workflows that go beyond whatever Trimble has set up as a baseline. They might add requirements for carriers to prove they can handle dangerous goods, or refrigerated cargo, or high-security transport. The product owner described these users as configuring within a system that Trimble has set up, rather than setting up the system itself. Whether there should be a hard distinction between internal Trimble admin capabilities and customer admin capabilities is something the product owner flagged as not yet decided — it was posed as a question worth thinking about.
**Customer viewers or end users** are people within a customer organisation who use Trimble products but whose role in the vetting context is to see information rather than configure anything. A freight procurement manager using Marketplace might see, when looking at carrier bids, that a given carrier has been vetted and what that vetting covers. They would not configure the vetting workflows — they would consume the output.
**Carriers and partners being vetted** are the companies or individuals on the other side of the vetting relationship. In Phase 1 these are carriers — logistics companies that transport goods. In future phases, the intent is to extend this to any type of partner. These users interact with Partner Vetting primarily to provide information: uploading documents, answering questions, and completing whatever the configured vetting workflow requires of them. They do this through interfaces embedded within the products they already use — Marketplace, a carrier onboarding portal, a transport management system — rather than through a separate application. Crucially, carriers would also have their own view of their vetting history: they would be able to see what they have been vetted on, for which shippers, and manage their profile.
An important complication here is that the distinction between "party being vetted" and "party doing the vetting" is not clean. The same entity can occupy both roles simultaneously. A carrier being vetted by a shipper might also subcontract loads to other carriers and want to vet those subcontractors themselves. In that case, the carrier is both a subject of vetting workflows configured by someone else and an administrator of vetting workflows they have configured for their own purposes. This dual-role reality has direct implications for how permissions and roles are modelled — the system cannot assume a clean separation between the two sides of the vetting relationship. Any role and permissions model must accommodate an entity being a vetted party in one context and a vetting administrator in another, potentially within the same session or product.
**External customers with no existing Trimble product relationship** are a future category. The product owner described a scenario where a company that does not use any Trimble logistics product could nonetheless purchase Partner Vetting as a standalone product. They would bring their own carrier or partner data, authenticate through their own identity system, and use Partner Vetting to vet those partners. This is explicitly a later-phase consideration, not Phase 1, but it was described with enough specificity that it needs to be held in mind as an architectural constraint from the beginning.
**Agent or automated consumers** are not human users at all but systems — ARC being the primary example — that call Partner Vetting through its MCP or API interfaces to read vetting information, trigger vetting workflows, or create new configurations. The product owner explicitly mentioned that it should be possible for an external customer's agent to connect to Partner Vetting's MCP server and, through that agent, create and manage vetting workflows programmatically.
---
## 6. Core Intended Functionality
The core of what Partner Vetting does is allow someone with the right permissions to define what they need to know about a partner, have that information collected from the partner, validate it, and present the results in a way that is useful across products and contexts.
**Vetting workflows** are the central unit of configuration. A vetting workflow, in the product owner's description, is a defined set of things that a partner needs to demonstrate or provide in order to be considered vetted for a particular purpose. A workflow might require a carrier to upload a dangerous goods certificate. Another might require them to confirm they have English-speaking drivers available. Another might check that their EU transport license is valid and will remain so for at least three months. The checks within a workflow can range from hard document validation — where AI cross-references an uploaded document against an authoritative external source — to simple questions that the partner answers directly.
The product owner had a strong vision for how workflows would be created. Rather than requiring administrators to fill in structured forms or navigate configuration trees, the intention is that workflow creation would be conversational — through a chat interface where the user describes in natural language what they want to achieve. The system would interpret this, construct the workflow, and present it visually for the user to review and confirm. The product owner described this explicitly as a suggestion and a direction to explore rather than a hard requirement, and noted that if better options exist they should be proposed.
**Checks** are the individual verifiable items within a workflow. Some checks are validated against external sources — government portals, regulatory APIs, insurance management systems. Others are self-declared by the partner. Each check has a validity dimension: some expire (a cargo insurance certificate expires on a specific date), some need to be refreshed periodically (every quarter, twice a year), and some are one-time confirmations. The system needs to track the state of each check, know when it is becoming stale, and trigger re-collection before expiry. The product owner used the example of a 30-day advance warning when a document is approaching expiry.
**At-engagement vetting** is a specific pattern the product owner described in some detail. Rather than vetting carriers in advance through a standing process, there are scenarios where vetting is triggered at a specific moment in a workflow — for example, when a carrier accepts a bid on Marketplace and the load involves dangerous goods. At that moment, the system would recognise that the shipper's configured workflow requires the carrier to have a dangerous goods certificate, check whether the carrier already has one on file, and if not, prompt the carrier to provide it before the allocation can be confirmed. The carrier would be able to complete this inline — within Marketplace, not in a separate application — through injected UI. The product owner was clear that this should use the same underlying model and infrastructure as standing vetting, not a separate system.
**Workflow library and sharing** is an idea the product owner raised around how configured workflows would be managed. Multiple administrators within a customer organisation might contribute workflows. The product owner suggested there should be a shared library — workflows visible to the whole company — as well as possibly user-specific workflows. They noted that in the beginning, starting with company-level shared workflows is probably sufficient, and user-level workflows could be a later addition. This was expressed as a suggestion, not a hard requirement.
**Re-use of prior vetting across shippers** is an important functional intention. If a carrier has already been vetted for dangerous goods by one shipper, and a different shipper on the platform requires the same dangerous goods vetting, the system should be able to recognise that the carrier already holds the relevant validated information and surface that automatically — without requiring the carrier to go through the process again. This is dependent on having a consistent way to describe and match vetting requirements, which is part of why the product owner emphasised the importance of consistent language and naming across the system. This re-use idea is one of the more commercially significant differentiators the product owner described.
**Visualisation and badges** across products is another key functional element. Once a carrier has been vetted, that vetting information should be visible throughout the Trimble product ecosystem wherever carriers appear. The product owner described this as badges, hover states, or informational panels — visual indicators that a carrier has been vetted, that can expand to show more detail about what was verified and to what standard. These visualisations would be injected into existing products through web components. The product owner was clear that these should be per-check or per-workflow in their provenance — not a single aggregate "verified" label — so that the basis for the signal is always visible.
---
## 7. The Partner Profile Concept
A central idea in the product owner's description is that each partner being vetted has a profile within Partner Vetting. This profile is not the same as the partner's record in any other system. It is a vetting-specific overlay — a place to store the documents, validated results, workflow statuses, and consent records that Partner Vetting owns, linked to but not duplicating the canonical partner record held elsewhere.
Ownership of this profile, in the product owner's framing, belongs to the partner — not to any individual customer or to Trimble. This is presented as a deliberate and important design principle, and it is one of the lessons drawn from a previous failed attempt at something similar (referred to as Trust Center, which is documented in a separate post-mortem that was referenced but not shared in this conversation). The failure of Trust Center is attributed in part to the friction it created for carriers — presumably because the value exchange was not clear or because carriers did not feel ownership of their own data. Partner Vetting is explicitly designed to give carriers genuine ownership and genuine value in exchange for their participation.
The profile should accumulate over time. Each time a carrier completes a vetting workflow, the results are stored against their profile. If a carrier is vetted for dangerous goods for one shipper, that fact is part of their profile. If they are later vetted for refrigerated transport for a different shipper, that is added. Over time, the profile becomes richer and more valuable — both to the carrier (who can demonstrate their capabilities more broadly) and to the ecosystem (which can make faster, more reliable trust decisions).
Carriers would have a view of their own profile within whatever product they are using, and potentially in a dedicated section of the carrier-facing onboarding application that already exists within Trimble. They would be able to see what they have been vetted on, for which customers, what the status of each validation is, and what is expiring. They would be able to manage consent — deciding which shippers or products can see which parts of their profile.
The consent model is important but not yet fully specified. The product owner described it as something where a carrier can choose to expose certain vetting results broadly — for example, making their Trimble-validated status visible to all shippers on Marketplace — or keep certain validations restricted to the specific shipper who requested them. The exact mechanics of how consent is granted, scoped, and revoked are not yet worked out and were flagged as something that needs to be thought through carefully, with legal implications acknowledged.
---
## 8. How It Would Be Consumed — Web Components
The primary UI delivery mechanism the product owner described is web components — modular, self-contained UI elements that can be injected into existing applications without those applications needing to build their own vetting interfaces.
The rationale is straightforward: Partner Vetting needs to appear inside many different existing Trimble products. Marketplace, transport management systems, slot booking tools, visibility platforms, carrier onboarding applications — all of these are separate products, some built in React, some in Angular, with their own UI, their own navigation, and their own user context. Building a separate standalone application for each of them would be impractical. Injecting web components allows Partner Vetting's UI to appear contextually within these products without requiring each product team to build anything beyond the embedding.
The product owner described several types of components that would be needed. There would be components for configuring vetting workflows — available to users with configuration permissions. There would be components for viewing vetting status — available to users who need to see whether a carrier is vetted and to what degree. There would be components for carriers or partners to submit their information — upload documents, answer questions, manage their profile. And there would be lightweight visualisation components — badges, hover cards, status indicators — that could be embedded wherever a partner entity appears in a product.
The product owner emphasised that the documentation and cataloguing of these web components must be treated as first-class from the very beginning of development, not as an afterthought. There should be a well-maintained, publicly accessible web component catalog with clear documentation on how to use each component, what parameters it accepts, what it renders, and what context it requires. This was stated as a strong intention rather than a suggestion.
The product owner also raised, as a rough idea worth exploring, whether components might in some cases be generated dynamically — constructed on the fly based on the specific context rather than being fixed, pre-built elements. They were uncertain whether this was a good idea and explicitly flagged it as something to investigate rather than a direction already chosen.
---
## 9. How It Would Be Consumed — APIs and MCP
The product owner described three consumption surfaces for Partner Vetting: web components (covered above), APIs, and an MCP server.
APIs would allow products to interact with Partner Vetting programmatically — triggering vetting workflows, querying the status of a carrier's vetting, or registering new partners — without necessarily using the web component UI. This is important because carriers and partners are not always added through user interfaces. Many Trimble products support bulk or automated operations through APIs, and those flows should also be able to interact with Partner Vetting. The product owner noted that internal and external APIs might be the same, differentiated only by authentication and authorisation, though this was not stated as a firm decision.
An MCP server would allow agent-based consumers — including ARC — to interact with Partner Vetting as a skill. The product owner described this as central to how Partner Vetting fits into the broader ARC ecosystem. ARC calls skills through MCP. But the MCP surface is not only for ARC: the product owner explicitly said that external customers who have their own agents should also be able to connect to Partner Vetting's MCP server and, through that, create workflows, query results, and consume the service. This makes MCP not just an internal integration mechanism but a genuine external-facing interface.
A further concrete use case for the external API and MCP surfaces is worth noting explicitly. Because carriers own their validated profile data, they can use these interfaces to expose their credentials to parties entirely outside the Trimble platform. A carrier could direct an external partner — a shipper they work with who does not use any Trimble product — to query the Partner Vetting API or MCP and retrieve their validated information directly. This is not a theoretical edge case; it is a deliberate expression of the data ownership principle and a meaningful part of the carrier value proposition. It means the validated data is genuinely portable and usable beyond the Trimble ecosystem, which strengthens the carrier's incentive to participate in the vetting process in the first place. The design of the external API and MCP surfaces should treat this as a first-class use case, not an afterthought.
As with web components, the product owner stated that documentation for both the APIs and the MCP server must be first-class from the start. All three surfaces — web components, APIs, MCP — should have clear, well-structured, publicly accessible documentation and catalogs. This is a strong intention. The framing was that anyone who wants to work with Partner Vetting should be able to consult the documentation and understand immediately how to do so.
---
## 10. Data and Integration Considerations
One of the most important principles the product owner articulated concerns data ownership, and it must be stated precisely to avoid a misunderstanding that could distort architectural decisions. Partner Vetting does not own the master data for carriers, users, or tenants. Those records — who the carrier is, who the user is, which company they belong to — exist in other systems and are authoritative there. Partner Vetting interfaces with those systems to resolve identity and understand context, but it does not replicate or take ownership of that master data.
However, Partner Vetting does fully own all of the data its service produces. This includes: vetting workflow configurations, uploaded documents submitted by partners, validation results, workflow statuses, consent records, and the audit trail. This data is created by Partner Vetting, lives in Partner Vetting's systems, and is Partner Vetting's responsibility. The product owner was explicit that these two things must not be conflated — "we don't own the data" is not the correct framing. The correct framing is that we don't own master records for entities that exist elsewhere, but we absolutely own everything we create and produce.
Trimble has a central database used for billing purposes that contains records for every carrier the company works with. Each individual product also maintains its own carrier database with product-specific attributes, linked back to the central billing record through some form of identifier. The product owner acknowledged that the linkage mechanisms are not always clean or fully understood. Partner Vetting would need to interface with the central billing database to understand the carrier population, and potentially also with individual product databases to access more granular carrier characteristics. The mechanism for doing this — listening to events, polling, direct API calls — is not yet decided. The product owner noted this as an important area of complexity.
For users, the intention is that Partner Vetting does not store user records at all. Instead, it would resolve user identity at request time through Trimble's existing identity system (referred to as Trimble ID). It would store role assignments — which users have which permissions in which context — but names, email addresses, and other user attributes would come from the identity system on each request, not from a local store.
For external customers — particularly the future scenario where a company with no Trimble product relationship uses Partner Vetting — the same principle would apply, but the identity source would be the customer's own authentication system rather than Trimble ID. The product owner described this as linking through some form of federated identity, though the specifics were not elaborated.
The question of whether to use event-driven architecture — for example, a message bus such as Kafka — was raised explicitly by the product owner as an open question. They were uncertain whether this level of infrastructure is necessary or appropriate, and flagged it as something to investigate as part of the architectural design process. This was not presented as a preference for or against event-driven architecture, just as a genuine open question.
---
## 11. ARC and Skill Integration
ARC is Trimble's internal initiative to build an omnipotent AI agent that can be accessed within any Trimble product as a side panel or overlay. It presents as a chat interface. Users type or speak to it. ARC consults a catalog of skills and orchestrates them to complete tasks. The skills in the catalog are capabilities — some built by Trimble, potentially others contributed externally.
Partner Vetting is intended to be a skill in ARC's catalog. Commercially, it would be offered and licensed as a single skill called Partner Vetting. Internally, it would be composed of many sub-skills — granular capabilities such as "validate cargo insurance" or "create vetting workflow" — that ARC calls as needed.
The technical mechanism by which ARC calls skills is MCP. ARC calls an MCP server, and the MCP server exposes the tools that the skill provides. For Partner Vetting, the MCP adapter would be a thin layer sitting in front of the actual Partner Vetting service, translating between the MCP protocol and the service's internal API. This means the Partner Vetting service itself does not need to be coupled to ARC or to the MCP protocol — only the adapter layer does.
The product owner indicated they would share documentation on how ARC works in more technical detail so that the MCP server for Partner Vetting can be designed appropriately. That documentation was not yet provided in this conversation.
---
## 12. Phase 1 Scope and Intended Starting Point
Phase 1 is intended to prove the core concept with a real customer and a real use case. The first customer is Knauf — a large German shipper. The decision to start with Knauf rather than with an internal Trimble product was made and closed as of the date of the architecture document (May 7, 2026). There was dissent on this point from one member of the team (Alexei), who preferred starting with an internal Trimble product. That dissent is recorded but the decision stands.
Phase 1 scope is intended to include the rebuilding of what Vera does today — the four checks (VAT, company registration, cargo insurance, EU transport license) — but reimplemented against a new, properly designed data model and service architecture. This is not a port of Vera. It is a reimplementation that treats Vera's check semantics as the first ruleset in a new system, while the system itself is built to accommodate many different rulesets, many different checks, and many different tenants from the beginning.
Phase 1 is intended to be a single-customer build, but one where the data model and component design are explicitly built for multi-tenancy — so that adding a second customer is a configuration exercise rather than a build exercise.
The web component family, the MCP adapter, the carrier profile, the consent model, the audit and billing infrastructure, and the role architecture are all intended to be in Phase 1. The vetting workflow creation UI, with its chat-driven approach, is intended to be in Phase 1 for the configuration experience.
What is explicitly deferred to Phase 2 and beyond includes: customer self-service check authoring, network signal integration (using Trimble's shipment and movement data as a vetting signal), hierarchical carrier profile graphs (carrier → division → country entity), external customers without existing Trimble product relationships, and the onboarding of additional Trimble products as tenants.
---
## 13. Future Directions and Extensions
The product owner described a number of directions that are not Phase 1 but that need to be held in mind architecturally.
**Carriers vetting shippers** is one of the more interesting future directions. The product owner noted that carriers often have bad experiences with shippers — not being paid on time, being made to wait without compensation, disputes over terms. A system that allows carriers to provide information about their experiences with shippers, and that surfaces that information to other carriers considering working with those shippers, would be a meaningful extension of the trust network in the opposite direction. This was described as a future possibility rather than a committed direction.
**Subcontractor vetting** addresses a very common logistics practice. Carriers frequently subcontract loads to other carriers — often informally, through phone calls with known contacts. Large carriers do this strategically and at significant volume. If subcontracting is happening within the ecosystem of a Trimble product, there is an argument that the subcontracted carrier should also be subject to vetting. The product owner raised this as another possible revenue stream and as an extension that the architecture should accommodate.
**Performance scores and execution data** would add a layer beyond document-based vetting. Rather than just verifying that a carrier holds the right credentials, the system could eventually incorporate data about how carriers actually perform — delivery punctuality, KPI scores, reliability ratings. This would turn the partner profile from a compliance record into something more like a trust and performance profile. The product owner acknowledged this is a significant extension and firmly placed it in the future, not Phase 1.
**Expansion beyond logistics** follows directly from the decision to call the product Partner Vetting. Once the core vetting infrastructure is proven in logistics, the intention is to offer it to other industries — construction, agriculture, forestry, and others — where companies work with partners they need to vet. The underlying mechanisms (workflow configuration, document collection, AI validation, profile management) are industry-agnostic if the architecture is built correctly.
**External customers without Trimble products** is the version of the product that stands entirely on its own — where a company has no Trimble relationship and buys Partner Vetting as their entry point. They would bring their own partner data, use their own identity system, and leverage Trimble's pre-vetted carrier network as a resource. This is a significant commercial extension that would require federation of identity, API-first or MCP-first onboarding, and careful thinking about data isolation.
---
## 14. Open Questions and Uncertainties
The following questions were either explicitly raised as open by the product owner or emerge clearly from the discussion as unresolved.
**Should there be a hard distinction between internal Trimble admin capabilities and customer admin capabilities, or should these be handled purely through role and permission configuration?** The product owner raised this question and did not resolve it.
**What is the right mechanism for interfacing with external carrier databases?** The linkage between Partner Vetting, the central billing database, and individual product-specific carrier databases is acknowledged as complex. Whether to use direct API calls, event streams, periodic synchronisation, or another mechanism is not decided.
**Is an event-driven architecture appropriate?** The product owner explicitly raised this as an open question — whether a message bus such as Kafka should be part of the architecture. They did not express a preference, only that it needs to be investigated.
**What is the exact consent model for the carrier profile?** The principle — that carriers own their profile and can control who sees what — is clear. The mechanics of how consent is scoped, granted, and revoked, and what happens to previously shared data when consent is revoked, need to be worked out. Legal review was flagged as necessary before launch.
**How should vetting workflows be authored?** The product owner's strong intuition is a conversational, natural language interface. This is proposed as the primary mechanism but explicitly flagged as a direction to explore rather than a firm decision.
**Should web components be pre-built and fixed, or dynamically generated?** The product owner raised dynamic generation as a rough idea but was uncertain about it.
**What is the right tech stack — language, framework, database, messaging?** Explicitly deferred. The product owner stated that tech stack decisions should be made last, once all functional and non-functional requirements are understood and ADRs are established.
**How does the MCP server for Partner Vetting fit precisely into ARC's skill model?** Additional ARC documentation is expected but not yet provided.
**What is the pricing and billing model?** The product owner noted that carriers completing vetting on their own initiative should be free, while checks triggered by a shipper or tenant should be billable events. The specific pricing model — per-vetting, subscription, tiered — is deferred.
**What is the right hosting model for the carrier-facing submission interface?** Should it be injected into an existing carrier portal (such as Marketplace's carrier-facing portal if one exists), or should a standalone carrier-facing host be built?
**Does Knauf require hierarchical carrier profile structure (carrier → division → country entity), or is a flat profile sufficient for Phase 1?** This requires a workshop with Knauf to determine.
---
## 15. Development Approach and Constraints
The way Partner Vetting is being built is unusual and deserves its own section, as it is both a constraint on and a context for the architecture.
The team building Partner Vetting consists of six people split into three pairs. The first pair — the product pair — is responsible for everything related to defining and building the product itself. Neither of the two people in this pair is a software engineer by training, though both have engineering knowledge. The hypothesis they are testing is that two non-engineers, armed with AI tools and a well-configured pipeline, can build a product of this scale entirely through AI-generated code. Every line of code in the system will be produced by AI. No human will write code directly.
The second pair — the skills team — is responsible for building the tools and capabilities that enable the product pair to do their work. This includes AI skills for ideation, design, documentation creation, specification writing, code review, and research. Their job is to make the product pair as capable as possible by equipping them with the right tools.
The third pair — the infrastructure and self-healing team — is responsible for two things: building the orchestration layer that takes bugs, routes them through the pipeline, and ensures they are resolved without manual intervention; and building the mechanisms for monitoring, alerting, and automated correction in the deployed system.
The governing constraint of the entire development approach is that **no code ever changes without a specification**. Every change to the codebase — whether a new feature, a bug fix, a refactoring, or a test — must be triggered by a written specification. Specifications are the only valid input to the code generation pipeline. This is not a preference; it is a hard rule of how the team operates.
The product owner expressed a strong intention to ground the product in domain-driven design principles — using a well-defined ubiquitous language, identifying bounded contexts, and ensuring that the names and concepts used in the code match the names and concepts used in the product and in conversation. However, this was explicitly stated as an intention and a goal for the design process, not as a language or taxonomy already established. The ubiquitous language does not yet exist; establishing it is part of the work ahead.
Design system governance is important. Because the product will be delivering UI through web components injected into many different host applications, there needs to be a clear, well-governed design system that defines how components are built, what they look like, and how they behave. This prevents fragmentation and ensures consistency across all the contexts in which Partner Vetting appears.
Documentation is a first-class concern from the very beginning. The web component catalog, the API documentation, and the MCP server documentation must all be maintained with the same care as the code itself. They should be public, well-structured, and approachable — not afterthoughts produced at the end of development.
The architecture should be AI-first in the sense that the system is designed to work naturally with LLMs — both in how it is operated (through conversational interfaces) and in how it calls external systems. Internally, the validation logic relies on AI to interpret documents and cross-reference external sources. The system should be architected so that calling other MCP servers, consuming external APIs, and interacting with other agents is natural and well-supported.

## 📜 Partner Vetting — Legacy Requirements

This page supplements the Partner Vetting — Product Context Document. It records architecturally relevant constraints, patterns, and operational realities from the existing Carrier Vetting / Vera system that are not captured in the Product Context Document. Its purpose is to ensure that decisions about the new system's architecture are informed by what exists today.
---
## Event and Trigger Model
Vera processes documents asynchronously. Analysis is triggered automatically whenever a carrier uploads a document or enters a VAT number — the upload event fires a POST to the analysis endpoint, and the result is retrieved later via a separate GET endpoint polled for completion status. This is a fire-and-poll pattern rather than a synchronous request-response or a push callback. The implication for the new system is that the event model must accommodate asynchronous document analysis as a first-class concern: triggers should be clearly defined (upload event, VAT entry event), analysis jobs must be trackable by state, and callers must be able to query job status without blocking. An admin can also manually initiate AI analysis for a specific section or for all sections in one call, meaning the trigger can be either system-generated (on upload) or human-initiated (on demand).
## Check Definition Data Model (Prompt Configuration Layer)
Administrators configure specific yes/no questions for each document section in the vetting workflow. Vera uses these questions to guide its AI analysis and determine pass/fail for each section. The expected response format for each prompt is a structured JSON object: `{"answer": true/false, "reason": "..."}`. Prompt configuration is supported at the country level — different prompt sets can be defined per country — and saved prompts are reused across runs. The architectural implication is that the new system requires a check definition schema capable of encoding: the question text, the expected answer, the section it belongs to, and the country or context scope. This configuration layer is the machine-readable description of what "valid" means for each check, and it must be versioned and auditable.
## Retry and HITL Escalation Contract
On analysis failure (where the AI agent cannot produce a valid structured response), Vera retries the analysis up to three times. If all retries are exhausted, the system marks the job as an error, saves the error message to the database, and creates a Jira ticket for a human administrator to perform manual verification. In the auto-approval flow, both the valid and invalid paths emit a Slack notification with cumulative approval status. The architectural implication is that the new system must define a structured escalation contract: a maximum retry count, a clear error state distinct from document-invalid states, a durable record of the failure reason, and a routing mechanism to a human review queue. Slack-based notification is the current operational channel for HITL handoff, but the new system should treat notification channel as a configurable concern rather than a hard dependency.
## Vera's Carrier Communication Limitation
Vera does not communicate rejection decisions or reasons to carriers. When Vera marks a document as invalid or leaves it in a pending state requiring manual review, human operators are responsible for reading Vera's internally generated reason, verifying the document themselves, writing a rejection comment, and manually sending it to the carrier. This limitation means that the communication layer between the vetting system and the carrier is entirely human-mediated today. The new system must decide explicitly whether automated carrier communication is a capability it will own (requiring a notification and messaging surface for the carrier-facing interaction) or whether it will preserve the current human-in-the-loop communication model. Either way, the architecture must include a clearly defined carrier communication responsibility boundary.
## Full Submission Status State Machine
Each carrier submission has a submission-level status and per-document statuses. The submission-level statuses are:
- **Pending** — all required documents have been uploaded and the submission is awaiting review (automated or human)
- **Missing** — one or more required documents have not been uploaded; the carrier cannot be reviewed until these are provided
- **Approved** — all documents have been verified and the carrier has been granted the vetted status
- **Rejected** — one or more documents failed verification
- **Expired** — a previously approved submission has had a document (typically cargo insurance) expire; the system automatically blocks platform access and requests a new upload; once the carrier submits a new document, the submission re-enters the Pending state and must be re-verified
Per-document statuses are: **Valid**, **Invalid**, **Pending**. The Expired state is architecturally significant because it is the only state that triggers automatic enforcement (access block) without human action, and it creates a re-entry loop back to Pending on new document upload. The new system must model Expired as a first-class state with its own transition rules, distinct from Rejected, and must implement the automatic access-gating side effect that accompanies it.
## Data Freeze During Verification
The current system enforces a data immutability rule tied to verification state. Before verification has started, a carrier can freely change their data and changes are immediately visible. Once verification is initiated, changes are blocked — the carrier cannot modify their submitted data while it is under review. After a successful verification, any change to previously verified data triggers a re-verification requirement, and the system notifies the carrier that Transporeon will review the change. This creates two distinct mutability states: free-edit (pre-verification) and locked (in-verification), with a transition to conditional-edit (post-verification, where edits are permitted but automatically trigger re-verification). The new system must model this state machine explicitly in its data layer, as it defines which fields are writable at which lifecycle stages and what side effects data mutations produce.
## Conditional Document Requirements Driven by Fleet Type
The EU transport license requirement is conditional on the carrier's fleet type. Asset-based carriers (those who own and operate their own trucks) must provide an EU transport license. Carriers who select "Subcontracted Only" as their fleet type are exempt — the EU license requirement is waived. In practice, when a carrier uploads an incorrect document in the EU license slot (e.g., a national driving licence), operators do not reject the submission outright; instead they change the carrier's fleet type to "Subcontracted Only", which retroactively removes the EU license requirement. This is a concrete example of a carrier attribute (fleet type) conditionally gating a document requirement. The new system must support configurable conditional logic where check requirements are expressed as rules that evaluate carrier profile attributes, not as a fixed document checklist. The fleet type gate is the existence proof for this pattern.
## Non-EU Carrier Gap and Country-Specific Requirements
The current system applies EU-based vetting logic to all carriers regardless of origin, causing failures for non-EU carriers who do not hold EU-specific documents such as the EU Transport License. The documented short-term resolution is to require only three documents for non-EU carriers (VAT ID, Company Registration Letter, Cargo Insurance) and skip the EU license check entirely. The long-term resolution is a per-country requirement structure, which has been partially documented for eight priority non-EU countries: Albania, Bosnia and Herzegovina, Montenegro, Norway, Serbia, Switzerland, Turkey, and Ukraine. For each of these, the equivalent of the EU transport license is a nationally issued road haulage permit, and the VAT equivalent is a country-specific tax identification number (e.g., NIPT for Albania, JIB for Bosnia, PIB for Serbia, CHE for Switzerland, VKN for Turkey, EDRPOU for Ukraine). The architectural implication is that the check definition schema must be able to express country-scoped requirement variants — a "transport license" check resolves to different document types, different validation sources, and different mandatory/optional rules depending on the carrier's country of registration.
## North America Vetting Stack (FMCSA)
North America vetting uses the FMCSA API, keyed on the carrier's DOT number, to verify three things: company type (broker, carrier, etc.), operating status, and safety rating. In addition to the FMCSA check, carriers must provide two insurance documents: liability insurance and cargo insurance. Platform access (specifically the ability to bid on loads) is gated on having valid insurance — if insurance expires, the carrier is blocked from bidding until new valid insurance is submitted. Minimum insurance coverage thresholds are enforced per shipper: P&G is documented as a concrete example of a shipper whose specific minimum coverage amounts are automatically applied when evaluating whether a carrier's insurance qualifies. This per-shipper configurable threshold is a distinct architectural pattern from the EU model: the same insurance document may be valid for one shipper and insufficient for another, depending on the shipper's configured minimums. The new system must support per-tenant (per-shipper) parameterisation of numeric thresholds within a check definition.
## Profile Fields Collected but Not Verified
Several carrier profile fields are collected during the North America onboarding flow but are neither validated by the system nor made mandatory. These include: MC number, SCAC code, Diversity category, number of trucks, truck and trailer types, and the ratio of own-operated vs. subcontracted fleet. The system accepts whatever the carrier self-declares for these fields without cross-checking against any authoritative source. This establishes a meaningful distinction between two categories of carrier data: **verified data** (fields that have been validated against an external authority and can be relied upon) and **collected data** (fields that exist in the profile but carry no validation guarantee). The new system's data model must explicitly encode this distinction — both for data integrity purposes and because consumers of the profile (e.g., shippers, matching algorithms) need to know which fields are trustworthy and which are self-declared.
## Dual Legacy System Fragmentation
The current EU vetting workflow spans two separate systems: the HCS platform (where tickets are created and managed) and the Marketplace back-office portal (where document review and status updates occur). Due to system integration limitations, operators cannot see all submissions from a single surface — they must check both systems manually. The documented SOP explicitly requires an end-of-day review in the back-office to catch any submissions that may have only appeared there without creating an HCS ticket. This dual-system fragmentation is a known operational pain point and a source of missed submissions. The new architecture is expected to eliminate this fragmentation by providing a single, unified surface for all vetting work items. Any new system that preserves a split between a ticketing/queue layer and a review/action layer must ensure that the two are tightly coupled with no gap where submissions can fall through.
## Human Review SLA and Automation Rate Baseline
The current operational SLA for human review of carrier submissions is 24 hours — the Transporeon team is expected to review and decide on any pending submission within one business day of it entering the queue. Vera automates approximately 80% of document checks, with the remaining 20% requiring human judgment (typically due to illegible documents, atypical document formats, or edge cases the AI cannot resolve with confidence). These two numbers — 24-hour SLA and 80% automation rate — are the current-state baselines that the new system is expected to match or exceed. They define the minimum acceptable performance bar for the HITL pipeline design: the automation layer must handle at least 80% of cases, and the human review queue must be designed to process the residual volume within 24 hours.
## Multilingual Document Processing
Documents submitted by carriers arrive in 25 or more languages. The current Vera system already handles this as a capability requirement for its document AI layer. The new system must treat multilingual document processing as a hard non-functional requirement for any document analysis component, not an enhancement. This constrains the choice of document AI models and pipelines — any approach that works only for a small set of languages is architecturally insufficient. The 25+ language figure applies specifically to EU and adjacent-country carriers; North American expansion would add further language coverage requirements.
## Carrier-Initiated Self-Vetting Flow
The Discovery Brief explicitly describes a carrier-initiated consumption pattern distinct from admin-triggered vetting: a carrier should be able to say to the ARC agent "vet my credentials for shipper Y" and have the system access and execute the carrier vetting skill on their behalf. This is a separate entry point from the current back-office admin flow. It implies that the vetting system must support a carrier-as-principal invocation model — where the carrier initiates a vetting run against a specific shipper's requirements, rather than waiting for the shipper or admin to trigger it. The new system's permission model, API, and MCP surfaces must accommodate this entry point as a distinct actor pattern with its own authentication context and rate-limiting considerations.
## Cross-Product Identity and Vetting Outcome Propagation
The current vetting outcome (the "Verified on Transporeon" badge) is tightly coupled to the Marketplace back-office status. Separate Trimble product lines maintain independent carrier databases with no shared vetting state. Moving vetting to ARC creates an unresolved labelling and propagation problem: a carrier vetted through the new system could be described as "ARC-vetted", "Vera-vetted", or "customer-vetted" depending on who initiated and funded the vetting — and these are not interchangeable claims. The Discovery Brief explicitly calls out that the cross-product identity strategy (matching, deduplication, confidence scoring) and the propagation plan (sync rules, ownership, latency, auditability) are unresolved. The current workflow already spans HCS and Marketplace back-office as a demonstration that cross-system propagation is a recurring design concern. The new architecture must define explicit rules for how a vetting outcome created in Partner Vetting propagates (or does not propagate) to other Trimble products, and what label and provenance it carries when it does.
## Audit Trail Migration Requirement
The current audit trail for vetting decisions lives in the Vera / Marketplace back-office system. The Discovery Brief identifies that as part of transitioning to ARC, the audit trail should migrate to Applied AI Safety and Enablements best practices. This is a migration constraint on the new system: it is not sufficient to build a net-new audit trail in isolation. The migration path from the existing audit record (what decisions were made, by whom, when, and why) to the new system's audit infrastructure must be defined, and the new system must be compatible with whatever the Applied AI Safety and Enablements team specifies as their audit standard.
## Company Registration Document Flexibility Policy
The team is not legally authorised to mandate official government-issued company registration documents. As a result, the system accepts alternative documentation that demonstrates a company is legally operating — including VAT registration confirmations, tax certificates, and internally issued company documents containing standard business details (company name, address, bank account number, etc.). An official government-issued company registration document is accepted if voluntarily provided but cannot be required. Critically, each document in the submitted set must serve a unique purpose: a cargo insurance document cannot simultaneously serve as proof of company registration. Every document slot must be filled by a document whose primary purpose aligns with that slot. This "unique purpose" rule is a validation constraint that must be modelled explicitly — the system cannot simply accept any document in any slot based on content overlap. The new system's document validation rules must encode both the flexibility in document type and the uniqueness-of-purpose constraint.
## Validation Validity Window
The target re-examination period for a completed vetting is 6–8 months. Once a carrier is verified, the expectation is that the full vetting process should be repeated within this window. The triggering mechanism for initiating re-examination is not yet defined — it is explicitly left open in the source documentation. Individual document expiry (e.g., cargo insurance expiring) already triggers a targeted re-verification of that document; the 6–8 month window is a broader re-examination of the entire submission. The new system must model validity at two granularities: per-document expiry (driven by the document's own expiration date) and submission-level re-examination (driven by elapsed time since last full verification, with a target window of 6–8 months).
## Expansion Vectors with Competitive Analysis
The Discovery Brief contains a structured evaluation of seven strategic expansion vectors for the Partner Vetting capability. These define which extensibility patterns the core architecture must leave room for, as each represents a distinct data model or processing capability:
- **Expand carrier documents vetted and depth (continuous monitoring / Smart COIs)** — Low/Medium effort, High revenue potential. Requires real-time integration with insurance management systems and continuous monitoring rather than point-in-time checks. Competitors: Highway, RMIS, MyCarrierPortal, SaferWatch, Carrier Assure, Certificial.
- **Shipper vetting / inverse vetting** — Medium effort, Medium revenue potential. Requires the system to treat shippers as subjects of vetting workflows, not just administrators of them. Competitors: Carrier Logistics Inc. (FACTS A/R Risk), Optimal Dynamics, SiftedAI, TransCredit, UPS Capital.
- **Forestry / deep-tier sustainability and ESG vetting (EUDR compliance)** — High effort, High revenue potential. Requires supply chain depth beyond direct carriers, integration with sustainability data sources, and EUDR/CSDDD compliance logic. Competitors: TRACT, Trimble Forestry, Sourcemap, FlyPix AI, Osapiens.
- **Account takeover and post-login behavioural vetting** — Medium/High effort, High revenue potential. Requires capturing and analysing behavioural signals post-authentication, which is architecturally distinct from document-based vetting. Competitor: CrossClassify.
- **Schedule-level asset vetting** — Medium/High effort, High revenue potential. Requires tracking specific vehicles (VINs), equipment serial numbers, and locations in real time, not just organisational-level credentials. Competitor: Certificial.
- **Link analysis for network-wide fraud detection** — High effort, High revenue potential. Requires graph-based analysis of relationships between carriers, brokers, and addresses to detect double-brokering rings and identity fraud networks. Competitors: CrossClassify, Highway.
- **Pre-shipment customs and regulatory vetting** — Medium/High effort, High revenue potential. Requires validating import/export documentation against regulatory frameworks (FDA, EUDR, TRACES NT) before shipment departure. Competitor: VeriPura.
The architectural implication is that the check definition schema, the profile data model, and the integration layer must be designed to accommodate not just document-based verification of legal entities, but also real-time data feeds, behavioural signals, graph relationships, and asset-level tracking — even if only document-based verification is implemented in Phase 1.
## Auto-Approval Runtime Toggle
The auto-approval design includes a UI-accessible toggle that allows operators to enable or disable automated approval processing at any time without a deployment. When the toggle is off, all submissions remain in human review regardless of Vera's assessment. This is an operational safety mechanism that allows the team to pause automation if confidence in the AI's output drops or during incident response. The new system should preserve this pattern as a runtime operational control — a feature flag or circuit breaker on the automated decision pathway that can be activated by an authorised operator without requiring a code change or deployment.
## Profile Service as a Distinct Component Boundary
The auto-approval design shows that the AI analysis component calls a separate Profile Service to update carrier status (valid or invalid) after completing its assessment. The analysis engine and the profile state store are treated as distinct services with a defined interface between them. This service boundary has architectural significance: the profile service owns the authoritative vetting status for a carrier, and the analysis engine writes to it through an API call rather than directly to a shared database. The new system should maintain this separation — the component responsible for AI analysis should not own the state it writes to, ensuring that profile state can be updated by multiple sources (automated analysis, human override, expiry jobs) without tight coupling to any single update path.

## Partner Vetting — Architecture Proposal (Proposal 2)

# Partner Vetting — Architecture Proposal (Proposal 2)
*Proposal 2 of two. Source: synthesis page distilled from PCD + LR + ARC integration documents. Authored under the constraint that every line of the implementation will be produced by autonomous AI codegen — no human PRs, no human review. The document commits the choices that codegen needs to be deterministic about; everything else is left to design docs.*
**Why this TOC.** Adopted from synthesis §10 unchanged. Drivers → QAs → domain → C4 levels 1–3 → data → integrations → cross-cutting → deployment → phasing → architecture/design boundary → risks → metrics → glossary (sub-page) → ADRs (flat sub-pages). Each section earns its place: section 6 Components is intentionally short — bounded contexts are where the design carries weight, and the components inside each context are at the boundary between architecture and design.
---
## 1. Drivers and goals
### 1.1 What's broken
Trimble carries \~200,000 carrier accounts across its logistics products. Roughly 35,000 are active on Marketplace. Vera — the internal tool that vets carriers today — covers about 6% of that active set. Of the 65 % that gets through Vera's automated layer, the rest sits in a manual review queue split across two systems (HCS for ticketing, the Marketplace back-office for review). Operators audit at end-of-day to catch what fell through the gap. The state of that overall vetting layer:
- **Single-product**: locked to Marketplace; no signal flows to TMS, visibility, or the rest of the Trimble portfolio (LR §«Cross-Product Identity and Vetting Outcome Propagation»).
- **Single-shape**: four checks (VAT, company registration, cargo insurance, EU transport license), no per-tenant parameterisation, no per-country variants beyond ad-hoc shoehorning (LR §«Non-EU Carrier Gap and Country-Specific Requirements»; §«North America Vetting Stack (FMCSA)»).
- **Stale-by-design**: snapshot vetting. A cargo insurance certificate uploaded today and cancelled tomorrow looks valid for the rest of its face validity. The structural ceiling Vera sits under is \~65–75 % real compliance for the same reason RMIS sits there.
- **Carrier-invisible**: the carrier does not see what was vetted, cannot port their validated credentials anywhere else, and learns about rejections by human-mediated email.
The cost of leaving this in place: regulatory exposure (EUDR by 2026-12-30, CSDDD, LkSG — fines up to 4 % of EU turnover), trust exposure in spot freight (strategic cargo theft up \~1,500 % since 2022 in North America; median nuclear verdict at \$51M in 2024), and commercial exposure (insurance premiums up 36–38 % over the decade as a partial consequence). Competitors (Highway, Certificial, Hwy Haul) are closing on the agentic identity layer in North America. None has the combination of a 200K-carrier network, European regulatory depth, and ARC-class agentic distribution. That is the gap Partner Vetting fills.
### 1.2 Goals
- **G1 — Make vetting a first-class capability across every Trimble product**, not a Marketplace-internal back office. Surface it as a skill ARC (Mario) can invoke from any host product, and as a family of embeddable web components in those products.
- **G2 — Carrier-owned, portable profile.** The carrier uploads documents and answers questions once. The validated outputs accumulate against a single profile they own, that they can grant visibility on to any tenant, that they can revoke, and that they can expose outside the Trimble ecosystem on their own initiative.
- **G3 — Per-tenant configurable vetting** without per-tenant build work. A tenant configures workflows from a catalog of checks; only Platform Admins author checks. Reuse across tenants is a network effect: if Carrier A is vetted by Tenant X for cargo insurance ≥ €1M coverage, the same validated artefact answers Tenant Y's "≥ €750K" rule with no re-collection.
- **G4 — Survive autonomous codegen as the build mechanism.** Every line of code is AI-generated against a written specification (synthesis C1). The architecture exists to give that pipeline machine-verifiable boundaries: typed contracts at every seam, opinionated invariants codegen cannot violate, exhaustive automated tests as the sole quality gate, observability that surfaces drift without humans.
- **G5 — Operable inside ARC's automated skill-lifecycle gates** (ARC-SL). No manual review step on deploy. Skills move from draft → published through automated static, runtime, and agent-level confidence checks; degraded confidence demotes the skill at runtime.
- **G6 — Multi-tenant from v1.** Knauf is the only customer at launch; the data model, isolation mechanism, and component design treat onboarding tenant N+1 as a configuration exercise.
### 1.3 Non-goals (v1)
- **Vera carry-over.** Migration of Vera's existing audit trail, in-flight submissions, and historical decisions is not a v1 workstream. The new system is target; carry-over is a separate workstream after v1 is confirmed working (synthesis Q24).
- **Customer self-service check authoring.** Tenants configure rulesets from the catalog. Authoring check primitives stays Platform-Admin-only in v1; opening it up is Phase 2.
- **Network-signal-based vetting.** Using Trimble's shipment, payment, and movement data as a vetting input is Phase 2 (the synthesis Network Signal stub).
- **External customers without an existing Trimble product relationship.** Phase 3. v1 federates only Trimble ID.
- **Hierarchical partner graphs (carrier → division → country sub-entity).** Flat profile in v1. Pulled forward to v1 only if the Knauf workshop establishes a hard requirement (synthesis Q15).
- **REST/HTTP public API.** MCP is the sole external programmatic surface in v1 and v2; see [ADR-010](https://www.notion.so/36099f3e507f81afae47d297eca8ae38) and synthesis §6 / Q8 for the decision.
### 1.4 Solution overview
Partner Vetting is a modular monolith on Trimble Transportation Cloud (TTC, Azure). Four bounded contexts — Profile & Consent, Document Intake & Authentication, Rules, and a Network Signal stub — share one PostgreSQL with row-level security as the tenant boundary. v1 ships **two end-user surfaces**: an MCP server (Mario, external customer agents) and a **standalone Partner Vetting Portal** — a TTC-hosted single-page app behind Trimble ID login that mounts the five Web Components (Status Card, Workflow Configuration, Vetting Dashboard, Partner Submission, Partner Profile) with role-based routing for Platform Admin, Tenant Admin, Tenant User, and Partner. The portal is the v1 validation venue; embedding the same components into other Trimble products (Marketplace, TMS family) and into Transporeon Registration Center is Phase 2 work. A private internal HTTP boundary backs the components and is never exposed to external callers. Document AI is a thin provider-abstracted layer (Anthropic Claude proposed primary) with explicit confidence calibration; sub-threshold or retry-exhausted analyses route to a single unified human-review queue. The Phase-1 ruleset reimplements Vera's four checks against the new domain model — not a port — and lands country-resolution for the eight priority non-EU jurisdictions enumerated in LR. The tech-stack family ADRs (ADR-001 through ADR-015) are presented as **proposals subject to engineer review** — final commitments land with the review pass.
---
## 2. Quality attributes
Targets are committed where stated; *TBD* means the target lives in a design doc, not the architecture.
<table fit-page-width="true" header-row="true">
<tr>
<td>QA</td>
<td>Target</td>
<td>Mechanism</td>
<td>Source</td>
</tr>
<tr>
<td>Multilingual document processing</td>
<td>≥ 25 languages at parity with Vera's EU coverage; ≥ 30 once North America lands</td>
<td>Document AI provider abstraction with multilingual model selection per call; eval set per language family</td>
<td>LR §«Multilingual Document Processing»</td>
</tr>
<tr>
<td>Carrier UX friction</td>
<td>p50 ≤ 6 minutes from first credential request to first successful Coverage Report when no manual review is required; p95 ≤ 24 hours including human review</td>
<td>Inline at-engagement flow inside host product; Partner Submission Component reuses prior validated artefacts on grant; no separate carrier portal hop</td>
<td>PCD §7 (Trust Center post-mortem)</td>
</tr>
<tr>
<td>Automation rate</td>
<td>≥ 80 % of document checks resolved without human judgement (Vera baseline)</td>
<td>Document AI primary path; HITL only on retry exhaustion, confidence-below-threshold, or explicit attestation-required check</td>
<td>LR §«Human Review SLA and Automation Rate Baseline»</td>
</tr>
<tr>
<td>Human-review SLA</td>
<td>≤ 24 hours per pending submission</td>
<td>Single unified queue (replaces HCS + Marketplace back-office split); queue depth alert at 80 % of SLA budget; no two-systems hop</td>
<td>LR §«Human Review SLA and Automation Rate Baseline»; §«Dual Legacy System Fragmentation»</td>
</tr>
<tr>
<td>Document AI retry posture</td>
<td>3 retries on parser failure; durable error state on exhaustion; structured handoff with failure reason intact</td>
<td>Bounded retry budget per analysis job; failure reason persisted in Result Envelope; queue routing on exhaustion</td>
<td>LR §«Retry and HITL Escalation Contract»</td>
</tr>
<tr>
<td>Document AI confidence calibration</td>
<td>Per-check threshold, configured in check definition; default 0.85; below threshold routes to human queue</td>
<td>Confidence carried on every Result Envelope; threshold versioned with check definition; eval set per check primitive</td>
<td>LR §«Retry and HITL Escalation Contract»; synthesis §9.3</td>
</tr>
<tr>
<td>Audit immutability and provenance</td>
<td>Every state-changing operation emits one or more audit_events rows; rows are append-only and never updated; per-check provenance preserved with (check_id, check_version, evidence_uri)</td>
<td>Outbox-pattern audit emitter inside every context; static lint check enforces audit-on-state-change at compile time; no aggregate "verified" boolean anywhere in the schema</td>
<td>LR §«Audit Trail Migration Requirement»; PCD §6, §10</td>
</tr>
<tr>
<td>Tenant isolation</td>
<td>Hard isolation between tenants; cross-tenant data access only via explicit Platform Admin path with audit trail</td>
<td>PostgreSQL row-level security keyed off a per-request session GUC (`pv.current_tenant`) set from the validated bearer token; every tenant-scoped table carries `tenant_id`; integration tests assert RLS denial path</td>
<td>PCD §12; ARC-IP «How Arc Agent Secures Tokens»</td>
</tr>
<tr>
<td>Security posture</td>
<td>TLS 1.3 in transit; Azure-managed encryption at rest; application-layer Fernet AES-128-CBC + HMAC-SHA256 over carrier consent records and integration credentials; per-profile envelope keys for crypto-erasure</td>
<td>Azure Key Vault for secret and key custody; Key Vault rotation on a 90-day cycle; per-profile envelope keys destroyed in Key Vault on GDPR erasure (documents become unreadable, audit metadata retained)</td>
<td>ARC-IP; PCD §14; synthesis Q6</td>
</tr>
<tr>
<td>Availability</td>
<td>v1: 99.5 % monthly for MCP and Status Card endpoints; TBD for Workflow Configuration and Dashboard surfaces (lower-criticality)</td>
<td>TTC-managed Azure SQL and Blob SLAs underneath; single-region active; multi-region passive deferred to Phase 2</td>
<td>Implied; gap G1 in synthesis §8</td>
</tr>
<tr>
<td>Identity-resolution latency</td>
<td>p95 ≤ 150 ms for IdP attribute resolution on hot path</td>
<td>Redis cache (5-minute TTL) keyed by `(idp, subject)`; cache miss falls through to Trimble ID OIDC userinfo endpoint with bounded timeout</td>
<td>PCD §10</td>
</tr>
<tr>
<td>Observability shape</td>
<td>OpenTelemetry traces, metrics, and structured logs on every request; one drift-detection metric stream consumed by the self-healing pipeline (synthesis §9.1)</td>
<td>OTel SDK initialised per process; backend (Datadog / Grafana / New Relic / Azure Monitor) is a separate engineer-review-level decision; metric and log schemas defined in `observability-spec.md` (design doc); no-PII-in-logs enforced by lint</td>
<td>Synthesis §9.1; PCD §15</td>
</tr>
<tr>
<td>Testability under codegen</td>
<td>Every internal and external boundary expressed as a typed contract (JSON Schema for HTTP, MCP tool schema for MCP, TypeScript interface for in-process); ≥ 90 % branch coverage of business logic on both backend and frontend; property tests on every state machine transition</td>
<td>Schema-first development discipline; Pact contracts between MCP adapter and service and between components and internal HTTP; backend (Vitest + fast-check + testcontainers + Pact + eval-set harness) and frontend (Vitest + Playwright + axe-core for accessibility) test stacks per <mention-page url="https://www.notion.so/36099f3e507f81e59156df776f8f15e5"/></td>
<td>Synthesis §9.1; PCD §15</td>
</tr>
<tr>
<td>Documentation as deliverable</td>
<td>Public MCP tool catalog, public Web Component catalog, public-where-permitted API reference; updated in CI on every merge</td>
<td>Generated from typed contracts; CI fails if a tool/component lacks a published page</td>
<td>PCD §8, §9, §15</td>
</tr>
</table>
Three targets remain *TBD* and explicitly belong in the design doc: throughput envelope (requests per second per skill), capacity-cost model per vetting, and disaster-recovery RPO/RTO. They depend on the v1 capacity workshop with TTC, not on architectural choices.
---
## 3. Domain model and glossary
The glossary lives as a sub-page (§15) for direct linking from other Notion documents. The inline definitions below are the canonical ubiquitous language. Names in code match names in product match names in conversation (PCD §15, synthesis C11).
- **Partner** — any third party who can be the subject of a vetting workflow. v1 is restricted to carriers in logistics; the model is industry-agnostic by construction.
- **Profile** — the partner's vetting-specific record. Not a master record of the partner. Holds documents, validated results, workflow statuses, consent grants, and `external_ids[]` linking to canonical partner records elsewhere (Trimble central billing DB, product-specific carrier DBs, future external-customer master data). Exactly one profile per partner across all tenants.
- **Document** — an artefact uploaded by a partner that substantiates one or more checks. Carries an expiration date where applicable. Subject to the *unique-purpose-per-slot* rule (LR §«Company Registration Document Flexibility Policy»): a cargo insurance certificate cannot also occupy the company-registration slot, even if its content overlaps. Documents are immutable after upload; the carrier replaces by uploading a new document, which versions the prior one.
- **Check** — a versioned, reusable primitive: one verifiable item with a defined input (a document, a profile attribute, or an external query), a defined output (a typed Result Envelope), and a defined source of validation (external authority API, parser + cross-reference, or self-attestation). The Phase-1 check catalog contains 4 EU checks + 8 non-EU country variants of the EU transport license check. Platform Admins author checks; tenants do not.
- **Rule** — a predicate over a check's typed output payload plus a freshness window. `cargo_insurance.coverage_amount ≥ €1,000,000 AND cargo_insurance.expires_at > now() + 30d` is a rule.
- **Ruleset (= Vetting Workflow)** — a named, versioned bundle of rules defining what "vetted for purpose P" means for one tenant. Customer-facing term is **vetting workflow**; the internal term in code and audit events is **ruleset**. Tenants configure rulesets from the catalog; they do not author check primitives.
- **Vetting Run** — one execution of a ruleset against one profile. Carries `trigger_mode` (standing or at-engagement), `triggered_by` (subject and tenant), and `state` (running, awaiting_documents, awaiting_review, completed, expired). One Vetting Run produces zero-or-more Result Envelopes and exactly one Coverage Report at terminal state.
- **Result Envelope** — the typed per-check output of a Vetting Run. Wraps a check-specific extracted payload (insurance policy number, coverage amount, expiry, geographic scope; or EU transport license number; etc.) with metadata: `check_id`, `check_version`, `status ∈ {pass, fail, inconclusive}`, `confidence` (0–1), `evidence_uri` (blob URL + content hash), `executed_at`, `valid_until` (derived from document expiry), `triggered_by`. Heterogeneous payload, uniform envelope.
- **Coverage Report** — the per-Vetting-Run, per-rule classification emitted to the consumer. Each rule resolves to one of: `satisfied`, `missing`, `stale`, `version_downgraded` (the matched Result Envelope was produced under an older check version), `inconclusive`. There is no aggregate boolean. The shipper (or their agent) interprets — the system never auto-fails the partner.
- **Grant (= Consent Record)** — the partner's authorisation for a specific tenant to read specific parts of their profile. Grants are per-`(tenant, profile)` and per-section; default is opt-in. Revocation freezes future visibility but does not retroactively withdraw Coverage Reports already delivered to the tenant. See [ADR-017](https://www.notion.so/36099f3e507f81dd96dcc51c5fcba32d).
- **Tenant** — an organisation that consumes Partner Vetting. v1 = Knauf. Trimble products that consume the service are tenants in their own right (Marketplace as a tenant of Partner Vetting). v3+ external customers are tenants under their own IdP federation.
- **Role** — a user's permissions inside a tenant context (or the cross-tenant Platform Admin axis). Four roles in v1, see [ADR-016](https://www.notion.so/36099f3e507f81a2bb24df59b34e9f0e): Platform Admin, Tenant Admin, Tenant User, Partner. Role assignments are the only user-related data Partner Vetting stores; all user attributes (name, email, etc.) come from the IdP per request.
- **Trigger mode** — Standing (periodic re-examination, partner-initiated, batch onboarding) or At-Engagement (just-in-time inside a host product's transactional flow, e.g. Marketplace bid acceptance). Both share the entire domain model; only the entry point and the default ruleset differ (synthesis F7).
- **External IDs** — `(system, external_id)` pairs on Profile, Tenant, and Document, pointing to canonical records elsewhere. Used to correlate, never to replicate.
- **Submission State** — the lifecycle state of one Vetting Run from the partner's perspective: `Pending`, `Missing`, `Approved`, `Rejected`, `Expired`. `Expired` is first-class and distinct from `Rejected`: it triggers automatic access-gating side effects in host products, and re-upload re-enters `Pending` (LR §«Full Submission Status State Machine»).
- **Audit Event** — an immutable record of every state-changing operation. Append-only. Schema: `(event_id, occurred_at, tenant_id, actor_principal, on_behalf_of_user, action, entity_type, entity_id, before_state, after_state, evidence_uri?)`.
- **Billable Event** — an immutable record of every commercially metered operation. Separate from audit because retention, consumers, and schema differ. Schema: `(event_id, occurred_at, tenant_id, sku, partner_id?, ruleset_id?, vetting_run_id?, quantity, unit)`. Carrier-initiated vetting is not billable; tenant-initiated vetting is (PCD §14, F36).
- **Notification / Alert** — outbound message to a partner or to a tenant operator about a state change (document expiring, vetting run completed, grant revoked, etc.). Transport is configurable per (tenant, recipient_class) — v1 supports email and in-portal; Slack/push deferred (synthesis Q27).
The glossary sub-page (§15) lifts these as-is; it is the linkable reference surface.
---
## 4. System context (C4 Level 1)
Partner Vetting sits between three classes of caller and four classes of dependency.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/edb73b9f-1531-47c6-8123-850b49865eb6/01-system-context.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=434a7763271951dea60743a7ea67a5c21e794c268c8d41d7c3a7df0898b7f35e&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**Callers (left-hand side of the diagram):**
- **Mario (ARC agent)** invokes Partner Vetting as an MCP skill on behalf of an end user in a Trimble product. Patterns P1 (Mario in ARC UI, Trimble-ID user), P2 (Trimble product calls ARC with application token + user identity), and P3 (external product with user-scoped `arc_sk_` key) all land on the same MCP server (ARC-IP P1–P3).
- **Standalone Partner Vetting Portal (v1 primary surface)** — a TTC-hosted single-page app behind Trimble ID OIDC that mounts the five Web Components with role-driven routing. All v1 user roles meet here: Platform Admin (catalog stewardship), Tenant Admin (ruleset configuration), Tenant User (dashboards and Status Card views), Partner (profile + uploads + grants + history). The portal is also the controlled venue for end-to-end UI validation before any component is embedded in another host. See [ADR-019](https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50).
- **Trimble products as tenants (Phase 2)** — Marketplace, freight procurement, visibility, the TMS family — embed the same Web Components for in-product display and at-engagement vetting once the portal-validated v1 has shipped. They never call the service directly; the components fetch from the private internal HTTP boundary using a tenant-scoped session.
- **Partners (carriers)** interact through the Partner Submission and Partner Profile Components. In v1 the primary surface is the standalone Partner Vetting Portal; Transporeon Registration Center embedding is Phase-2 work alongside the broader product-embedding rollout.
- **External customer agents (v3+)** call the MCP server using their own IdP-federated tokens. Out of v1 scope but the surface is the same.
**Dependencies (right-hand side):**
- **External authoritative sources** — FMCSA (DOT-keyed company-type, operating-status, safety-rating), VAT registries (country-specific VIES + national equivalents), insurance management systems (the Certificial-class smart-COI integration is Phase-2 scope; v1 validates against the uploaded certificate plus cross-reference where available), national road haulage permit registries for the eight priority non-EU countries.
- **Identity providers** — Trimble ID via OIDC (v1, all Trimble-internal traffic); v3+ external customer IdPs federated through the same OIDC layer.
- **Document AI provider** — Anthropic Claude as primary, with a thin provider abstraction. Provider selection is part of the check definition; the abstraction exists to allow per-check provider override and second-model consensus on borderline confidence.
- **TTC platform services** — Azure SQL (PostgreSQL flavour), Azure Blob, Azure Cache for Redis, Azure Key Vault, plus an observability backend (Datadog / Grafana / New Relic / Azure Monitor — engineer-review-level choice). All from the TTC-vetted catalog, provisioned by DevOps.
**Audit and billable event consumers** (downstream):
- The Applied AI Safety & Enablements audit pipeline, once that team's standard is finalised. Until then, audit events stay in Partner Vetting's audit_events table and a documented export contract exists for the migration moment.
- Trimble Finance's billing pipeline, fed by billable_events via a documented export.
The boundary is sharp: Partner Vetting owns everything it produces (profiles, documents, vetting runs, audit, billing) and owns no canonical master data. Federation, not replication, on every master-data dimension (PCD §10, synthesis C9).
---
## 5. Containers (C4 Level 2)
One deployable unit on TTC: the **Partner Vetting service**. Inside it, four bounded contexts. Three adjacent layers wrap them: the MCP adapter (external surface for agents), the Web Component delivery layer (private HTTP for in-product UI), and the persistence layer (Postgres + Blob + Redis + Key Vault).
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/ce68fcdf-ecc9-4911-b8d4-776c681bb404/02-containers.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=3c0c75bab4c1f91a88ed6e1a4e873f35ad1525a52ea3025fd91329a3b04bd1b4&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**Bounded contexts:**
- **Profile & Consent** owns Partner, Profile, Document, Grant, and the `external_ids` resolver. It is the only context with write access to consent records. Read access from other contexts is via in-process function calls subject to the same RLS session as the originating request — never via a cached copy of consent state.
- **Document Intake & Authentication** owns the document upload pipeline, the document AI provider abstraction, the analysis job queue (Postgres `FOR UPDATE SKIP LOCKED`), retry/escalation, and the unified human-review queue. It writes Result Envelopes; it does not read or interpret rules.
- **Rules** owns Check, Rule, Ruleset, Vetting Run, Coverage Report, and the per-tenant ruleset configuration. It reads Result Envelopes from Document Intake (via the outbox), reads Profile attributes via Profile & Consent, and emits Coverage Reports. It is the only context that runs ruleset evaluation. Country-resolution logic (mapping a check primitive to its country-specific variant given the partner's country) lives here.
- **Network Signal (stub)** is a placeholder context in v1 — it owns nothing operational, only an empty interface contract (`get_network_signal(partner_id, signal_class)`). The shape is reserved so Phase-2 work can drop in shipment/payment/movement signals without re-architecting Rules.
**Adjacent layers:**
- **MCP adapter** translates between the MCP protocol and the internal API. It enforces the ARC integration patterns (P1/P2/P3 token shapes), per-`(auth_principal, tenant)` rate limits, and the `actor` parameter that propagates end-user identity through agent invocations (Q10). It is intentionally thin — no business logic, only protocol translation and authentication.
- **Web Component delivery** is a static asset host (Azure Static Web Apps, TTC) serving the five Web Components **plus the standalone Partner Vetting Portal** application that mounts them with role-based routing. The portal is the v1 surface; Phase-2 embedding in host Trimble products (Marketplace, TMS, Transporeon Registration Center) consumes the same components. The internal API and the MCP adapter share the service layer underneath; both terminate at the same set of bounded-context entry points.
- **Persistence** is single-Postgres for v1 (with RLS as the isolation mechanism), Blob for documents, Redis for caches and rate-limit counters, Key Vault for secrets and per-profile envelope keys.
Why a modular monolith and not microservices or event-driven services: see [ADR-008](https://www.notion.so/36099f3e507f8181ba18fc11b03151e1). The short version is that the codegen pipeline produces deterministic, testable output more reliably against a cohesive monolith than against a distributed system, the team is six non-engineers with a two-month v1 deadline, and the four contexts share enough referential integrity (profile ↔ vetting run ↔ result envelope ↔ coverage report) that the network cost of separating them buys nothing the in-process module boundary doesn't already deliver. Module boundaries are enforced by import-linter rules (cross-context imports fail CI), not by network calls.
---
## 6. Components
The significant internals per context. Components are at the architecture/design boundary — named here so the design docs know what to specify, but module-internal structure (class layouts, function signatures, file organisation) belongs to design.
### 6.1 Profile & Consent
- **Profile Aggregate** — the partner's canonical Partner Vetting record. Mediates writes from Document Intake (new documents, new result envelopes) and Rules (new vetting runs, new coverage reports). Enforces the one-profile-per-partner invariant. Also serves the read path for the Partner Profile Web Component (history of vetting runs, document library, shipper-connection list, grants).
- **Consent Manager** — issues, lists, and revokes grants. Wraps the Key Vault calls for per-profile envelope keys: a `delete_profile` operation destroys the key and emits the GDPR-erasure audit event; document blobs and consent records become unreadable but audit metadata remains.
- **External-ID Resolver** — looks up canonical partner records in the Trimble central billing DB and product-specific carrier DBs. Lazy pull on demand, no event subscription (synthesis Q12). Cached for 5 minutes in Redis.
- **Document Store Adapter** — wraps the Azure Blob client; computes content hashes; persists `(blob_uri, content_hash, mime, content_length, uploaded_at)` on Document. Documents are write-once.
### 6.2 Document Intake & Authentication
- **Upload Endpoint** — multipart upload terminator; rejects malformed payloads; emits the upload event to the job queue.
- **Analysis Job Queue** — Postgres table consumed via `FOR UPDATE SKIP LOCKED`. Workers pull jobs, call the document AI provider through the abstraction, persist Result Envelopes, emit retry/escalation events. Bounded retry budget per job (3 attempts, exponential backoff with jitter, max 60s).
- **Document AI Provider Abstraction** — single interface (`extract(check_id, check_version, blob_uri) → ResultEnvelope`) implemented per provider. Anthropic Claude as v1 primary; Azure Document Intelligence reserved as fallback for cases where Anthropic capacity is the bottleneck. Provider selection per check definition.
- **Escalation Router** — on retry exhaustion or confidence-below-threshold, routes to the unified human-review queue with the original failure reason preserved on the envelope.
- **Human Review Queue** — single in-portal surface, no Jira/HCS dependency. Operators see all pending items in one list, claim, decide. Replaces today's HCS + Marketplace back-office split (LR §«Dual Legacy System Fragmentation»).
- **Auto-Approval Toggle** — runtime flag on the Rules-driven auto-approval pathway. When off, every Vetting Run lands in human review regardless of envelope confidence. Preserves the operational safety pattern from LR §«Auto-Approval Runtime Toggle». Toggle state is per-tenant.
### 6.3 Rules
- **Check Catalog** — the read-only registry of Check definitions. Versioned. Phase-1 entries: VAT (EU + 8 non-EU country variants), Company Registration (EU + non-EU variants per LR), Cargo Insurance, EU Transport License (with `Subcontracted Only` exemption rule), FMCSA bundle (DOT-keyed, North America scope), Liability Insurance (North America scope).
- **Ruleset Configurator** — accepts ruleset definitions from tenants (via Workflow Configuration UI or MCP `create_ruleset`), persists versioned rulesets. Rulesets reference checks by `(check_id, check_version)`. Country-resolution rules are first-class predicates inside rulesets, not implicit.
- **Vetting Run Executor** — the state machine driver. Runs the ruleset against the profile, emits requests to Document Intake for missing or stale envelopes, waits, evaluates, terminates with a Coverage Report. Implemented as a durable Postgres-backed state machine; no in-memory orchestration; resumable across process restarts.
- **Coverage Report Builder** — per-rule classification (`satisfied` \| `missing` \| `stale` \| `version_downgraded` \| `inconclusive`). Never emits an aggregate boolean.
- **Country Resolver** — given a partner's country of registration and the check's country-aware definition, picks the right variant. Reads partner country from Profile via in-process call; falls through to the EU default only when explicitly permitted by the check definition.
### 6.4 Network Signal (stub)
- **Interface contract only.** A `get_network_signal(partner_id, signal_class)` shape returning a typed `inconclusive` envelope in v1. Phase 2 fills in shipment-history, payment-history, dwell-time, and similar signals from TTC products.
### 6.5 Shared substrate
- **Outbox emitter** — every context writes domain events to a single `outbox` table in the same transaction as the entity write. A background worker reads the outbox, dispatches to in-process subscribers (audit emitter, billable emitter, notification dispatcher), marks rows as delivered. Provides at-least-once internal delivery without an external bus (synthesis Q13 → no event bus in v1; see [ADR-007](https://www.notion.so/36099f3e507f812ea099d603fcd44a0d)).
- **Audit Emitter** — subscribes to outbox events; writes `audit_events` rows; never modifies them.
- **Billable Emitter** — subscribes to outbox events with `billable=true`; writes `billable_events` rows; never modifies them.
- **Notification Dispatcher** — subscribes to outbox events configured to notify; renders templates; dispatches via configured transport (email v1, in-portal v1).
---
## 7. Data architecture (logical)
Entities, relationships, lifecycle states, ownership, immutability, and tenant isolation. Physical schema details (indexes, partitioning, migration paths) live in the data design doc.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/2caec0cf-0ec1-4612-b985-3b0a0da94ac9/03-data-model.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=a02097e3318bd06bf5519000b8b58554fd8844a04540b4de822ee502062a84ff&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 7.1 Entity catalog
The synthesis §9.4 list, with v1 invariants:
<table header-row="true">
<tr>
<td>Entity</td>
<td>Owned by</td>
<td>Mutability</td>
<td>Notes</td>
</tr>
<tr>
<td>Partner</td>
<td>Profile & Consent</td>
<td>Mutable (attributes), immutable (id)</td>
<td>One per real-world partner. `external_ids[]` links to canonical records.</td>
</tr>
<tr>
<td>Profile</td>
<td>Profile & Consent</td>
<td>Mutable; document/result history is append-only</td>
<td>One per Partner. Pre-/in-/post-verification mutability gates per LR §«Data Freeze During Verification».</td>
</tr>
<tr>
<td>Document</td>
<td>Profile & Consent</td>
<td>Immutable after upload; soft-versioned on replace</td>
<td>Stored as `(blob_uri, content_hash)` reference; raw bytes in Blob.</td>
</tr>
<tr>
<td>Check (versioned)</td>
<td>Rules (Platform Admin)</td>
<td>Versioned, immutable per version</td>
<td>Catalog-managed. Tenants reference `(check_id, check_version)`.</td>
</tr>
<tr>
<td>Rule</td>
<td>Rules</td>
<td>Versioned with parent Ruleset</td>
<td>Predicate AST over Result Envelope payloads + freshness window.</td>
</tr>
<tr>
<td>Ruleset (= Vetting Workflow)</td>
<td>Rules (Tenant Admin)</td>
<td>Versioned per tenant; immutable per version</td>
<td>Tenants edit by creating a new version; old versions remain referenceable.</td>
</tr>
<tr>
<td>Vetting Run</td>
<td>Rules</td>
<td>State machine</td>
<td>One execution; one terminal Coverage Report.</td>
</tr>
<tr>
<td>Result Envelope</td>
<td>Document Intake</td>
<td>Append-only</td>
<td>One per check execution; multiple per Vetting Run.</td>
</tr>
<tr>
<td>Coverage Report</td>
<td>Rules</td>
<td>Append-only</td>
<td>One per terminal Vetting Run.</td>
</tr>
<tr>
<td>Grant (Consent Record)</td>
<td>Profile & Consent</td>
<td>Mutable (status toggles); changes append audit</td>
<td>Per-`(tenant, profile, section)`.</td>
</tr>
<tr>
<td>Tenant</td>
<td>Profile & Consent</td>
<td>Mutable</td>
<td>Configuration record; not a billing record.</td>
</tr>
<tr>
<td>Role Assignment</td>
<td>Profile & Consent</td>
<td>Mutable</td>
<td>`(user_subject, tenant, role)`. No user attributes stored.</td>
</tr>
<tr>
<td>Audit Event</td>
<td>Shared</td>
<td>Immutable, append-only</td>
<td>Every state-changing operation produces ≥ 1 row.</td>
</tr>
<tr>
<td>Billable Event</td>
<td>Shared</td>
<td>Immutable, append-only</td>
<td>Tenant-initiated vetting only; carrier-initiated is free.</td>
</tr>
<tr>
<td>Notification</td>
<td>Shared</td>
<td>Mutable status</td>
<td>Lifecycle: `queued → sent → delivered/failed`.</td>
</tr>
</table>
### 7.2 Lifecycle state machines
The two state machines that govern the experience:
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/98f7a8e5-eadd-4cd5-9fa2-64b28af049f7/04-submission-state-machine.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=41ef6aeeda94b863afdd74cc3dddbac8498a790d2ea864e6ded3f04dfe4e08f7&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**Submission states** (synthesis F37, LR §«Full Submission Status State Machine»):
- `Pending` — documents uploaded, awaiting analysis or review
- `Missing` — required documents not yet provided; partner is the next actor
- `Approved` — all rules `satisfied`; access enabled in host products
- `Rejected` — one or more rules failed; reasons in Coverage Report
- `Expired` — a previously approved submission has had a document expire; host-product access is automatically blocked; re-upload returns to `Pending` and re-runs verification
`Expired → Pending` on re-upload is the only state transition that fires without an actor's intentional action (the trigger is wall-clock crossing the expiry date). It is also the only transition that triggers an automatic host-product side effect (access block). Both behaviours are first-class architectural concerns.
**Vetting Run states** (internal, not exposed to partners):
- `created → running → awaiting_documents → running → awaiting_review → running → completed`
- `completed` is terminal and produces the Coverage Report. There is no `failed` state — failure is encoded as `inconclusive` rules in the Coverage Report. The system never auto-fails the partner.
### 7.3 Immutability rules
- **Audit events** never updated. The audit lint check fails the build if any code path emits an UPDATE against `audit_events`.
- **Billable events** never updated. Corrections are negating rows, never edits.
- **Documents** are immutable after upload. Carrier replaces by uploading a new document; the prior one is soft-versioned (kept in Blob with the prior content hash; not visible in the profile).
- **Result Envelopes** are append-only. A new envelope for the same `(check_id, document_id)` does not delete the old one; both are referenceable. The Vetting Run picks the freshest passing envelope when evaluating rules.
- **Ruleset versions** are immutable. Tenants edit by creating a new version. In-flight Vetting Runs continue against the version they started on.
### 7.4 Ownership
- Partner Vetting **owns** every entity in the table above.
- Partner Vetting **does not own** canonical Partner master records, canonical user records, or canonical Tenant master records. Those live in the Trimble central billing DB, Trimble ID, and product-specific systems. `external_ids[]` is the federation mechanism.
### 7.5 Tenant isolation
PostgreSQL row-level security keyed off a per-request session GUC `pv.current_tenant` (and `pv.current_principal_role` for Platform Admin escalation). Every tenant-scoped table carries a `tenant_id` column with an RLS policy of the form:
```sql
CREATE POLICY tenant_isolation ON <table>
  USING (
    tenant_id = current_setting('pv.current_tenant')::uuid
    OR current_setting('pv.current_principal_role') = 'platform_admin'
  );
```
The application's per-request middleware:
1. Validates the bearer token (Trimble ID OIDC or ARC-issued).
2. Resolves the principal's role assignment for the target tenant.
3. Sets `pv.current_tenant` and `pv.current_principal_role` on the connection.
4. Releases the connection back to the pool with the GUCs cleared on `RESET`.
Cross-tenant queries (Platform Admin only) emit a distinguishing audit event flagged `cross_tenant=true` so the audit pipeline can isolate that surface for review.
See [ADR-009](https://www.notion.so/36099f3e507f8116b7afe78e32d9a830) for the rejected alternatives (schema-per-tenant, app-layer scoping, DB-per-tenant) and why RLS wins for v1.
### 7.6 Profile data partitioning between verified and self-declared
Per LR §«Profile Fields Collected but Not Verified», the schema distinguishes verified data (validated against an external authority via a Result Envelope) from collected/self-declared data (MC number, SCAC, fleet composition, etc.). Two storage shapes:
- **Verified attributes** live as Result Envelopes against a check. The profile exposes a typed `get_verified(check_id) → Envelope?` reader that returns the freshest passing envelope.
- **Self-declared attributes** live on the Profile entity directly, marked with a `provenance='self_declared'` flag. Consumers of the profile (UI, MCP `get_profile`, Partner Profile Web Component) always see the provenance flag — the architecture forbids surfacing self-declared data as if it were verified.
---
## 8. Integration surface
Three consumption surfaces, in order of importance: MCP, Web Components, internal HTTP. Plus the outbound integration surface — external authoritative sources, IdPs, document AI providers, and audit/billing consumers.
### 8.1 MCP tool surface (v1)
MCP is the sole external programmatic surface in v1 and v2 ([ADR-010](https://www.notion.so/36099f3e507f81afae47d297eca8ae38); synthesis Q8). The v1 tool list, with stable schemas managed under the ARC skill-lifecycle gates:
<table header-row="true">
<tr>
<td>Tool</td>
<td>Caller</td>
<td>Purpose</td>
<td>Identity model</td>
</tr>
<tr>
<td>`start_vetting_run`</td>
<td>Mario, Trimble products, external agents</td>
<td>Trigger a Vetting Run against `(partner_id, ruleset_id, trigger_mode)`. Returns the run id and current state.</td>
<td>P1/P2/P3 + `actor.on_behalf_of_user`</td>
</tr>
<tr>
<td>`get_vetting_run`</td>
<td>Mario, Trimble products</td>
<td>Fetch one Vetting Run by id, with current state.</td>
<td>P1/P2</td>
</tr>
<tr>
<td>`list_vetting_runs`</td>
<td>Mario, Tenant Admin via Mario</td>
<td>Filter by `(partner_id, ruleset_id, trigger_mode, state)`.</td>
<td>P1/P2</td>
</tr>
<tr>
<td>`get_coverage_report`</td>
<td>Mario, Trimble products, external agents</td>
<td>Fetch the Coverage Report for a terminal Vetting Run.</td>
<td>P1/P2/P3</td>
</tr>
<tr>
<td>`get_profile`</td>
<td>Mario, Trimble products, partner (P1)</td>
<td>Fetch a profile under the caller's grants. Partner can fetch their own profile in full; tenants fetch only granted sections.</td>
<td>P1/P2/P3</td>
</tr>
<tr>
<td>`list_checks`</td>
<td>Mario, Trimble products</td>
<td>List available check primitives in the catalog. Read-only.</td>
<td>P1/P2</td>
</tr>
<tr>
<td>`list_rulesets`</td>
<td>Mario, Tenant Admin</td>
<td>List rulesets visible to the caller's tenant.</td>
<td>P1/P2</td>
</tr>
<tr>
<td>`create_ruleset`</td>
<td>Tenant Admin (via Mario or Workflow Configuration UI)</td>
<td>Create a new ruleset version from a list of `(check_id, check_version, rule_predicate)` entries.</td>
<td>P1/P2</td>
</tr>
<tr>
<td>`submit_document`</td>
<td>Partner via P1, or carrier-initiated via P3</td>
<td>Upload one document against a profile slot.</td>
<td>P1/P3</td>
</tr>
<tr>
<td>`submit_attestation`</td>
<td>Partner via P1</td>
<td>Provide a self-attestation answer (yes/no or free-text) for a check that does not require a document.</td>
<td>P1</td>
</tr>
<tr>
<td>`grant_visibility`</td>
<td>Partner via P1</td>
<td>Grant a tenant visibility over a profile section.</td>
<td>P1</td>
</tr>
<tr>
<td>`revoke_visibility`</td>
<td>Partner via P1</td>
<td>Revoke a previously issued grant.</td>
<td>P1</td>
</tr>
<tr>
<td>`request_document`</td>
<td>Tenant operator via Mario</td>
<td>Send a notification to the partner asking for a specific document.</td>
<td>P1/P2</td>
</tr>
</table>
Every tool schema is registered with the ARC skill catalog and subject to ARC-SL's automated quality gates (draft → published; degraded if confidence drops). Tool input/output schemas live in `mcp-surface.json` as the single source of truth; the MCP adapter, the documentation generator, and the Pact contract tests all consume that schema.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/4ee19780-07e3-4e97-bf27-2ad31c14c213/05-standing-vetting-flow.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=82eeeb5a6b768072aac9ad8e79f663ed5cfc70c23f9b7a75743cd42117046122&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/ff9173ba-542a-445b-a505-11b6f07dae9d/06-at-engagement-flow.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=026107dcdd20bf3f95ccfda97f3d70a7fa79fcf04445ab3c65cbc0c063902d10&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 8.2 Identity propagation through agent invocations
Per ARC-IP P1/P2/P3, every MCP call carries:
- The **agent principal** (Mario, or the external customer's agent), authenticated via the agent's own credential.
- The **end-user subject**, surfaced as a structured `actor.on_behalf_of_user` parameter on every tool that operates on user-scoped state. Audit events record both. The pattern is identical for carrier-as-principal invocations (synthesis F30): the partner's Trimble-ID subject is the `on_behalf_of_user`; the agent is the principal.
This matters for billing attribution: a Vetting Run triggered by a carrier (`actor.on_behalf_of_user` is the carrier; no `tenant` scope) is free. A run triggered by a tenant operator (`tenant` set; `actor.on_behalf_of_user` is the operator's Trimble-ID subject) is billable. The same MCP path serves both, distinguished only by the validated identity.
### 8.3 Web Component family
Five components, all framework-agnostic Custom Elements. Distributed from the same Web Component delivery layer; consumed by host products (and the standalone Portal) via a `<script type="module" src="...">` plus a custom element tag.
<table header-row="true">
<tr>
<td>Component</td>
<td>Tag</td>
<td>Hosts</td>
<td>Audiences</td>
</tr>
<tr>
<td>Status Card</td>
<td>`<pv-status-card>`</td>
<td>Marketplace carrier list, TMS carrier view, dashboard rollups</td>
<td>Tenant Users (view-only)</td>
</tr>
<tr>
<td>Workflow Configuration</td>
<td>`<pv-workflow-config>`</td>
<td>Tenant admin surface in any Trimble product</td>
<td>Tenant Admins</td>
</tr>
<tr>
<td>Vetting Dashboard</td>
<td>`<pv-vetting-dashboard>`</td>
<td>Tenant admin surface; standalone dashboard</td>
<td>Tenant Admins, Tenant Users</td>
</tr>
<tr>
<td>Partner Submission</td>
<td>`<pv-partner-submission>`</td>
<td>Standalone Partner Vetting Portal (v1); Transporeon Registration Center (Phase 2); v3+ standalone host</td>
<td>Partners — **active write flow**: upload documents, complete attestations, satisfy a specific Vetting Run</td>
</tr>
<tr>
<td>Partner Profile</td>
<td>`<pv-partner-profile>`</td>
<td>Standalone Partner Vetting Portal (v1); Phase-2 product embeds where partners need a home view</td>
<td>Partners — **home view**: profile summary (verified + self-declared, with provenance flags); document library; complete Vetting Run history across all tenants; shipper-connection list with grant management; active vs saved state separation</td>
</tr>
</table>
Each component takes a typed prop contract (TypeScript interface, exported as a JSON Schema) and emits typed custom events. Framework-agnostic Custom Elements remain the on-the-wire contract regardless of which library is used to build them — see [ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b) for the Lit-vs-React trade-off (proposed).
Components fetch from the private internal HTTP API. They are not allowed to call the MCP surface directly — that would expose the surface to browser-side credential handling that the security model deliberately forbids.
**On Partner Submission vs. Partner Profile.** Both are partner-role components but cover different shapes of work. Partner Submission is the *active write flow* — a focused, task-shaped UI for satisfying one Vetting Run (uploading a specific document, completing a self-attestation question, granting visibility for the run's tenant). Partner Profile is the *home view* — the partner's standalone surface where they see everything that's been recorded for them across every tenant: the profile summary (with explicit per-attribute provenance flags), the complete document library (current + soft-versioned prior uploads), the full Vetting Run history (active, completed, expired, with re-entry paths for Expired→Pending re-uploads), the shipper-connection list (which tenants hold active grants, with revoke controls), and an *active* state (in-flight runs and pending actions) separated from a *saved* state (historical, terminal records). This implements synthesis F17 directly. The two components share data (same Profile entity underneath) but render distinct views — and they can be embedded independently, since a host product wanting at-engagement vetting only needs Partner Submission, while a carrier portal wanting a full self-service home wants Partner Profile.
The Web Component catalog is a public deliverable from day one (PCD §8). It is generated from the typed contracts and published as part of the Documentation pipeline (§9.6).
**v1 host: the standalone Partner Vetting Portal.** All five components ship together inside a TTC-hosted single-page app behind Trimble ID OIDC login (see [ADR-019](https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50)). Role drives which components and views are visible. The portal is the controlled validation surface — engineers, design, and Knauf exercise the full UI in one place before any component is embedded in another Trimble product. Phase-2 onboarding of Marketplace, TMS, and Transporeon Registration Center reuses the same component set; embedding becomes a `<script type="module">` + custom-element-tag exercise against components the portal already proves out.
### 8.4 Internal HTTP boundary
Private, between Web Component delivery and the service layer. Authenticates via the same Trimble ID OIDC tokens carried by the host product's user session; rate-limited per `(user_subject, tenant)`. Not documented publicly. Not an external API. Schema lives in `internal-http.openapi.yaml` and is consumed only by the Web Components and the integration test suite.
### 8.5 External authoritative source integrations
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/c21ec529-0b43-49f3-8b5e-debad8fd9391/07-integration-surface.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=26e9e03f1889fb24523d317d529d19f89bc062669665235a36aaf63dea272244&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
Outbound integrations are wrapped per the stability patterns in §9.2:
- **FMCSA** — REST API, DOT-keyed. Timeout 2s, circuit breaker on \> 3 consecutive failures, fallback to `inconclusive` Result Envelope.
- **VAT registries** — VIES for EU; country-specific endpoints for non-EU. Same wrapper pattern.
- **National road haulage permit registries** (Albania, Bosnia, Montenegro, Norway, Serbia, Switzerland, Turkey, Ukraine per LR) — heterogeneous; some scraped, some API-based. Each gets a per-source adapter behind the same Provider interface as the document AI layer.
- **Insurance management systems** — Phase 2 (smart-COI integration à la Certificial). v1 validates against the uploaded certificate plus content cross-reference; live policy-status checks are deferred.
### 8.6 Outbound: audit and billing
- **Audit export** to the Applied AI Safety & Enablements pipeline once their standard ships. Until then, audit_events stays in Postgres; the export contract is a documented pull (their consumer reads `audit_events` over a read-only credential).
- **Billing export** to Trimble Finance. Billable_events is consumed via a documented pull on a daily batch cadence; near-real-time billing is not a v1 requirement.
### 8.7 IdP integrations
- **Trimble ID** — primary; OIDC; jose-class library for token validation; Authlib-class on the resource server. Userinfo endpoint called on cache miss only (5-minute Redis TTL).
- **External customer IdPs (Phase 3)** — federated through the same OIDC layer; per-tenant IdP configuration record.
---
## 9. Cross-cutting concerns
### 9.1 Codegen-first invariants
Autonomous codegen is the build mechanism. No human PRs, no human review. The architecture exists to give the codegen pipeline boundaries it cannot violate without the build failing. The invariants:
- **Typed contracts at every boundary.** MCP tool schemas in `mcp-surface.json`. Internal HTTP in `internal-http.openapi.yaml`. In-process module entry points as TypeScript interfaces. The Web Component prop contracts as JSON Schemas generated from TS interfaces. Generated client SDKs on every external surface so contract drift breaks the build.
- **Schema-first development.** A boundary contract changes by editing its schema first; codegen regenerates the implementation skeleton and the contract tests; failing tests refuse the merge. The schemas, not the code, are the source of truth.
- **Exhaustive automated tests as the only quality gate, on both sides of the stack.** Backend (proposed): Vitest for unit + integration, fast-check for property tests on every state machine transition, testcontainers for ephemeral Postgres/Redis, Pact for contract tests at every typed boundary, Vitest-based custom harness for AI eval-sets. Frontend (proposed): Vitest with `@open-wc/testing` (Lit) or `@testing-library/react` (React) for component tests, Playwright for end-to-end browser flows, `@axe-core/playwright` for accessibility. See [ADR-014](https://www.notion.so/36099f3e507f81e59156df776f8f15e5) for the full backend + frontend test stack with named alternatives.
- **Opinionated invariants the codegen cannot violate, enforced by lint:**
	- No `UPDATE` against `audit_events` or `billable_events`. (AST lint rule.)
	- No raw queries that bypass RLS. (Lint rule plus RLS denial-path integration tests.)
	- No PII in logs. (Lint rule against `console.log` of typed `Email`, `Name`, etc.; structured logger only.)
	- No cross-context imports outside the published context interface. (Import-linter rules.)
	- Every state-changing handler emits ≥ 1 outbox row in the same transaction. (Lint rule plus integration assertion.)
- **Observability that surfaces drift without humans.** Every Vetting Run produces a structured event with `(run_id, ruleset_id, ruleset_version, check_versions[], envelope_confidences[], terminal_state, duration_ms)`. The self-healing pipeline subscribes to this stream and triggers re-evaluation specifications when drift signatures fire (envelope confidence drift, terminal-state distribution drift, latency drift).
- **Specification-pipeline contract.** Every code change originates from a written specification (synthesis C1). The specification format is documented in the spec-pipeline design doc and references the schemas above as the contract surface the spec must respect. The architecture exposes: the schema set, the test harnesses, the lint rules. The spec pipeline must accept those as inputs and produce code that passes them as outputs.
- **ARC skill-lifecycle gates inherited.** The MCP adapter ships with ARC-SL's automated gates: static checks on tool schemas, runtime confidence monitoring per tool, agent-level confidence checks across tool sequences. No manual review step on deploy.
### 9.2 Stability patterns (Release It! / Nygard)
Autonomous codegen makes stability discipline a v1-day-one concern. No humans are catching production drift; the patterns must be in the code:
- **Timeouts** on every external call (FMCSA, VAT registries, insurance registries, Trimble ID userinfo, Anthropic Claude, Azure Blob, Azure Key Vault, internal Redis). Defaults: 2s for hot-path identity lookups, 10s for document AI extraction, 5s for authoritative-source lookups. Per-call override on the integration record.
- **Circuit breakers** on every external dependency, with documented behaviour on open: emit `inconclusive` Result Envelope, route the affected Vetting Run to the human queue, surface the dependency status in `/health/integrations`. Breakers reset on a successful probe call.
- **Bulkheads** between contexts: separate worker pools per context (one for Document Intake's analysis workers, one for Rules' Vetting Run executors, etc.). A stalled document AI provider cannot starve the Rules context.
- **Steady-state**: `audit_events` and `billable_events` partition by month; archived partitions move to cold Blob storage on a 90-day cadence. Document blobs follow a lifecycle rule: hot for 90 days, cool 90–365, archive after 365. Log rotation managed by the observability backend's ingestion-side retention.
- **Fail-fast** with typed error envelopes mirroring the Result Envelope discipline: every error response carries `(error_code, retryable, evidence_uri?, correlation_id)`.
- **Failure-mode tests** as first-class: every external integration has a chaos test (Toxiproxy + test harness) that asserts behaviour when the dependency is timing out, returning 500s, returning malformed payloads, or returning success with wrong identity. The chaos suite runs nightly.
### 9.3 Audit discipline
- Every state-changing handler emits ≥ 1 audit_events row in the same transaction as the entity write, via the outbox.
- Audit rows are never updated, ever. Lint and DB-level deny rules both enforce.
- The audit schema covers `(event_id, occurred_at, tenant_id, actor_principal, on_behalf_of_user, action, entity_type, entity_id, before_state, after_state, evidence_uri?, cross_tenant)`.
- Cross-tenant operations (Platform Admin only) flag `cross_tenant=true` so the audit consumer can isolate them.
- The export contract to Applied AI Safety & Enablements is a documented pull surface, not a push integration.
### 9.4 Observability shape
- **Instrumentation: OpenTelemetry** (proposed, see [ADR-011](https://www.notion.so/36099f3e507f81dc91b4f2568493869e)). Vendor-neutral; portable across backends.
- **Backend: engineer-review-level decision.** Candidates: **Datadog**, **Grafana Cloud / self-hosted Grafana + Prometheus + Loki + Tempo**, **New Relic**, **Azure Monitor**. Same instrumentation; different exporter configuration.
- **Traces**: OTel SDK on every request. Span per MCP tool invocation, per internal HTTP request, per outbox dispatch, per external integration call. Trace context propagated through `actor.correlation_id`.
- **Metrics**: standard four golden signals per tool and per integration; additionally, per-check `(envelope_confidence, latency_ms)` histograms; per-Vetting-Run terminal-state distribution; queue depth on the analysis job queue and the human review queue.
- **Logs**: structured JSON only. No-PII-in-logs enforced by lint (typed `Email`, `Name`, `Address` cannot be passed to the logger). Correlation id on every log line.
- **Drift-detection event stream**: the structured Vetting Run summary per §9.1 lands on a dedicated topic the self-healing pipeline consumes. The consumer integration shape depends on the chosen backend but the producer side is OTel-uniform.
### 9.5 Security posture
- TLS 1.3 in transit on every external surface.
- Azure-managed encryption at rest for all storage (Postgres TDE, Blob server-side encryption).
- **Application-layer Fernet AES-128-CBC + HMAC-SHA256** over carrier consent records, integration credentials, and document blob references (envelope-encrypted with per-profile keys). Inherits ARC's posture.
- **Per-profile envelope keys** in Azure Key Vault. The `delete_profile` operation destroys the envelope key — document blobs and consent records become unreadable while audit metadata is preserved. This is the v1 GDPR-erasure mechanism (crypto-erasure; synthesis Q6).
- **No tokens in LLM prompts or traces.** Lint rule against passing `Token`-typed values to logging or LLM-bound paths.
- **Per-****`(user, tenant, resource)`**** authorisation** evaluated at the service entry point. RLS enforces at the data layer.
- **Rate-limiting** at the MCP adapter and the internal HTTP layer: token bucket per `(auth_principal, tenant)`, default 60 RPM, per-skill override (synthesis Q11).
### 9.6 Documentation as deliverable
Public deliverables from day one (PCD §8, §9, §15):
- **MCP tool catalog** — generated from `mcp-surface.json`. One page per tool; input/output schema; examples; auth model; version history.
- **Web Component catalog** — generated from the component prop contracts. One page per component; props, events, hosts, examples, theming overrides.
- **API reference** — internal HTTP surface is *not* published publicly (it is private). MCP is the published programmatic reference.
- **Glossary** — the §15 sub-page, kept in sync with §3 by a CI check that diffs the two.
CI fails if a public surface element ships without a corresponding catalog page.
---
## 10. Deployment and operability
### 10.1 Topology
Modular monolith deployed as a single TTC service. One container image, multiple processes inside the container (API process, outbox worker, analysis worker, scheduled-task worker). Single-region active in v1 (West Europe); multi-region passive deferred to Phase 2 unless the Knauf workshop surfaces a regional requirement.
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/1abf17f0-c73e-4974-a688-e4045621cd5e/bb7b62a4-9992-4258-98da-8a2ed04b8850/08-deployment-topology.svg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466XQKBRGU7%2F20260516%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20260516T033701Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIE3ic7aljlUyeat3nhdFdBR5%2F3cGgR3r67IFuk5zon7gAiBzrUCiAkReOBvWy4bnpScXBk4KfhLmVzSLFhpAz8%2BAFCqIBAiE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDYzNzQyMzE4MzgwNSIM2%2B1iM5YiH1xZ6Mf2KtwDxzo3gtYXgHHaJy3HJdgcbOHL8xDuvLEfXZ6OsNoro%2FCBARBsxlYqiyTHO8H3%2BjMGF6vc5v1YdUOrCk6hHDeC1fkJBFt%2FVAojq0QRkgcEeQu%2FSwCnWSPZvkgG7ABIjsrhOQQ8UXHb4xjOd9aSCbqOZWoDg1P8QfXi6KmhdH%2FBrmsijH%2BaOwRc1QXvnw3DHmVS3LNzPQQDxyVsqUQ%2FuNo2u1syL3trNzACqBjxAGQbf1s68AyQ7TcB8GRhNlqnh9DdLx39lzv5MTa9Xgi%2BPM5oHXy%2FC06AjSG9eMHxrEYpzA30Y8%2FswYPBjjpPeTVDIKD1oxTHzuKpMr9FzNu7SSKqdkLNJgoJyCi3EChoCO2wIrweESpvMOQo39x5bAlu5Ozo1aAQdj%2BMAMHJe7l6v7%2Bid9LGjD%2F%2F3y2nvtdVk8WeM4n%2BXowlEbIKLx24hqtb7DmQtzmkOlj%2BLDrAHlfukRjy%2F2LqQzpzSrkLfIN%2BQTPvCr1UrANVT6nRHmbM%2BViALsfFUzfwkjjJ2Ve16OrJ7iI3ENKW5rDE7VJOmlNTJyfIczkpi7pDUhETActWjPM2TPZvmIB7RBYBeZReqkvLaDnukc0zXXEolg2Rx9gz8f4rXh0%2F5sjC6AvLf9HZJi0wubCf0AY6pgHccl%2Bz%2BHH2JHaeJnSD1MRqsIzhzwGgsSgY68U5MAcGFq%2FOmYeK04APnr%2F67vdnk8SwW6HM4bNJybKV4NI4RBcjeENVT9XYr24mSCJfKVvp5KD2zPqpHktorhmKh12fn0WIRRxJAyNA%2Fr55za9ZF30rAVnLM19IHBIo7S329%2BvUYU1zFfRwl36lNWmlWQNQ%2BJp3zH8vkAAh5th1IDn16Vv%2BYEg1reb6&X-Amz-Signature=f7695b1a8ac6d87c2bb8f3d8600c77c28af86020ec046e2488498ca62a201734&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
Components from the TTC catalog:
- **Azure App Service / Container Apps** — service host. TTC DevOps provisions.
- **Azure Database for PostgreSQL Flexible Server** — primary OLTP. Single instance in v1 with point-in-time backup and a read replica for analytics. RLS is the tenant boundary (§7.5, [ADR-009](https://www.notion.so/36099f3e507f8116b7afe78e32d9a830)).
- **Azure Blob Storage** — documents and Result Envelope evidence. Lifecycle rules per §9.2.
- **Azure Cache for Redis** — IdP attribute cache, rate-limit counters, short-lived integration response cache.
- **Azure Key Vault** — secrets, integration credentials, per-profile envelope keys.
- **Azure Static Web Apps** — Web Component delivery + standalone Partner Vetting Portal hosting. CDN-fronted.
- **Observability backend** — log/metric/trace aggregation behind the OpenTelemetry SDK. **Azure Monitor** is the TTC catalogue default; **Datadog**, **Grafana Cloud / self-hosted Grafana + Prometheus + Loki**, and **New Relic** are equally viable. Backend choice is engineer-review-level (see [ADR-011](https://www.notion.so/36099f3e507f81dc91b4f2568493869e)); OpenTelemetry instrumentation is invariant across them.
- **Azure API Management** — fronts the MCP adapter and the internal HTTP boundary. TLS termination, rate-limit pre-filter, request validation against the MCP and OpenAPI schemas.
### 10.2 Environments
- **Dev** — per-engineer ephemeral deployment slot inside a shared dev TTC subscription. Documents land in a dev-only Blob container. Document AI calls hit a sandboxed Claude credential with a separate budget cap.
- **Staging** — single shared instance, mirrors prod topology, fed by a sanitised replica of prod RLS-enforced data.
- **Prod** — single-region in v1.
### 10.3 Key rotation
- **Trimble ID OIDC signing keys** — rotated by Trimble ID; consumed via JWKS endpoint with a 5-minute Redis cache.
- **ARC skill credentials** (`arc_sk_` keys for P3) — rotated by ARC; per-skill rotation cadence is ARC-managed.
- **Per-profile envelope keys** — generated on Profile creation; rotated on a 90-day cycle; the rotation re-encrypts the consent record set under the new key inside a single transaction and leaves the prior key in Key Vault as a soft-deleted version until the audit-retention window passes.
- **Integration credentials** (FMCSA API key, VAT registry keys, document AI provider key) — rotated quarterly via Key Vault rotation policies; the application reads from Key Vault on cache miss (5-minute TTL).
- **Database admin credentials** — rotated by TTC DevOps via managed identity binding; the application never holds DB admin credentials.
### 10.4 Operability checklist (v1)
- `/health/liveness` and `/health/readiness` on every process.
- `/health/integrations` returns the open/closed state of every circuit breaker.
- The Auto-Approval Toggle (LR §«Auto-Approval Runtime Toggle») exposed at `/admin/auto-approval` per tenant; flipping it is a Platform-Admin action with audit emission.
- Backups: Postgres point-in-time recovery (7-day window in v1); Blob soft-delete enabled with a 30-day retention.
- Disaster recovery: RPO/RTO targets TBD pending the v1 capacity workshop.
---
## 11. Phasing
**Phase 1 (Knauf — v1)**
- Profile & Consent context fully built. Single tenant (Knauf) configured; multi-tenancy enforced from day one via RLS even with one tenant.
- Document Intake & Authentication context fully built. Three retries, durable error state, unified human-review queue, auto-approval runtime toggle.
- Rules context with the Phase-1 check catalog: VAT (EU + 8 non-EU country variants), Company Registration (EU + non-EU variants), Cargo Insurance, EU Transport License (with Subcontracted Only exemption). The Phase-1 ruleset reimplements Vera's four checks against the new model — not a port.
- MCP adapter with the v1 tool surface (§8.1).
- Web Component family (5 components): Status Card, Workflow Configuration UI, Vetting Dashboard, Partner Submission Component, **Partner Profile Component** (partner home view — profile summary, document library, vetting history across tenants, shipper-connection and grant management, active/saved state).
- **Standalone Partner Vetting Portal** — TTC-hosted single-page app behind Trimble ID OIDC, mounting the five components with role-driven routing for all v1 user roles. The portal is the v1 user-facing surface and the validation venue for end-to-end UI flows. See [ADR-019](https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50).
- Audit and billable event streams; daily pull contracts for the audit and billing consumers.
- Per-profile envelope-key GDPR crypto-erasure.
- Observability per §9.4 — OpenTelemetry instrumentation; backend selected during engineer review.
**Phase 2 (post-v1, \~3–6 months out)**
- **Embedding of the Web Component family into Trimble products as tenants** (Marketplace, TMS family) and into **Transporeon Registration Center** for the carrier-facing flow. Each onboarding is a configuration + embedding exercise against the same components the portal proves out in v1.
- Customer self-service check authoring — Tenant Admins can propose new check primitives via a Platform-Admin review surface.
- Network Signal context filled in with shipment-history, payment-history, dwell-time signals from Trimble product data.
- Smart-COI integration with insurance management systems (Certificial-class).
- North America vetting stack (FMCSA bundle, liability insurance check, per-shipper minimum-coverage thresholds per LR §«North America Vetting Stack»).
- Evaluation of Azure Service Bus if cross-product propagation requires fanout beyond the in-process outbox.
- Multi-region passive failover if required by enterprise customers.
**Phase 3 (v3+ external customers)**
- External customer IdP federation (OIDC).
- External-customer-agent MCP invocations under P3 with rate-limit and abuse-handling hardening.
- Hierarchical partner graphs (legal entity → division → country sub-entity) if Knauf or another enterprise tenant demands.
**Out of v1, explicitly deferred:**
- **Vera carry-over** (synthesis Q24). Migration of Vera's audit trail and in-flight submissions is a separate post-v1 workstream; the new system is target, not Vera-compatible.
- Expansion vectors per LR §«Expansion Vectors with Competitive Analysis» (continuous monitoring, shipper vetting, sustainability/ESG, behavioural vetting, schedule-level asset vetting, link analysis, customs vetting) — each is a Phase 3+ workstream against the same primitives.
---
## 12. Architecture-to-design-doc boundary
The architecture doc owns categorical decisions. Design docs own specific shapes. The boundary, per synthesis §9.5:
<table fit-page-width="true" header-row="true">
<tr>
<td>Architecture doc owns</td>
<td>Design docs own</td>
</tr>
<tr>
<td>Bounded contexts and their public interfaces</td>
<td>Module-internal structure, class layouts, function signatures, file organisation</td>
</tr>
<tr>
<td>Logical data model (entities, relationships, lifecycle states, immutability rules)</td>
<td>Physical schemas, indexes, partitioning strategies, migration scripts</td>
</tr>
<tr>
<td>Tech-stack families (proposed; subject to engineer review)</td>
<td>Specific library versions, framework choices within a family, build tooling</td>
</tr>
<tr>
<td>Boundary contracts (MCP tool surface, Web Component prop contracts, internal HTTP shape)</td>
<td>Concrete request/response payloads, validation rules, error catalogues</td>
</tr>
<tr>
<td>Cross-cutting concerns (observability shape, audit discipline, stability patterns, codegen invariants)</td>
<td>Concrete metric names, log formats, alert thresholds, dashboard layouts; observability backend selection</td>
</tr>
<tr>
<td>Deployment topology (modular monolith, single-region active)</td>
<td>Specific TTC resource definitions, container specs, deployment scripts, IaC modules</td>
</tr>
<tr>
<td>Tenant-isolation mechanism family (Postgres RLS)</td>
<td>Specific RLS policies per table, query helpers, RLS test harness</td>
</tr>
<tr>
<td>Identity model (Trimble ID OIDC, ARC-IP patterns, role-assignment storage)</td>
<td>Concrete IdP integration code, token cache implementation, role mapping tables</td>
</tr>
<tr>
<td>Codegen contract (what the architecture exposes to the spec pipeline)</td>
<td>Specific specification format, codegen pipeline implementation, prompts</td>
</tr>
</table>
The specification-pipeline contract: every code change originates from a written specification (synthesis C1). The architecture exposes the schema set (§9.1), the test harnesses (§9.1), and the lint rules (§9.1) as the contract the specification must respect. The spec pipeline must accept those as inputs and produce code that passes them as outputs. The spec format itself is in the spec-pipeline design doc.
---
## 13. Risks and open questions
Resolved in this doc (with ADRs):
- Roles (Q1, Q2) → [ADR-016](https://www.notion.so/36099f3e507f81a2bb24df59b34e9f0e).
- Consent model (Q4, Q5) → [ADR-017](https://www.notion.so/36099f3e507f81dd96dcc51c5fcba32d).
- GDPR erasure (Q6) → [ADR-015](https://www.notion.so/36099f3e507f81b59021ccf8184d85d7).
- Programmatic surface — REST vs MCP (Q8) → [ADR-010](https://www.notion.so/36099f3e507f81afae47d297eca8ae38).
- MCP tool surface v1 (Q9) → §8.1.
- Identity propagation (Q10) → §8.2.
- Rate limiting (Q11) → §9.5.
- External carrier DB integration (Q12) → §6.1 (Profile & Consent → External-ID Resolver).
- Event-driven architecture (Q13) → [ADR-007](https://www.notion.so/36099f3e507f812ea099d603fcd44a0d) (no bus in v1).
- Cross-product propagation (Q14) → [ADR-018](https://www.notion.so/36099f3e507f812cac5dc1c72db615b5).
- Knauf hierarchy (Q15) → flat in v1; revisit on Knauf workshop signal.
- Non-EU country variants (Q16) → Phase 1 covers EU + 8 priority non-EU per LR.
- Workflow authoring (Q17) → hybrid (visual primary, conversational helper). [ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b) covers the frontend implications.
- Web Components dynamic vs static (Q18) → static (parameterised) in v1, dynamic deferred. [ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b).
- Carrier-facing host (Q19) → **Standalone Partner Vetting Portal** in v1 (see [ADR-019](https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50)); Transporeon Registration Center embedding shifts to Phase 2 alongside Marketplace and TMS.
- Web Component tech stack (Q20) → [ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b) (Lit proposed; React alternative).
- Knauf v1 surface (Q21) → both — Mario via MCP and the standalone Partner Vetting Portal (which hosts the Workflow Configuration UI and Dashboard).
- Carrier communication ownership (Q26) → new system owns it via the Notification context.
- Notification transports v1 (Q27) → email + in-portal.
**Surviving open questions** (architecture doc did not close):
- **Q3 — External IdP federation specifics for v3+ customers** (OIDC vs SAML vs both; per-tenant configuration shape). Phase-3 decision; design-doc level work driven by the first external-customer engagement.
- **Q7 — Liability framework**. Counsel-owned. Determines whether the architecture must add live-policy-status APIs against insurance issuer registries; v1 assumes no (document-content-based validation + cross-reference). Trigger to revisit: counsel sign-off on the v1 liability framework.
- **Q22, Q23 — Pricing model**. Architecture-neutral (billable_events captures facts at whatever granularity the model needs). Decision belongs to commercial.
- **Q25 — Why Vera's coverage is \~6 %**. Adoption is a product/UX investigation, not an architecture decision. The architecture supports the four levers (in-product embedding, carrier-owned profile portability, network reuse across tenants, ARC-driven self-vetting); whether they move the number is for the rollout to demonstrate.
**Architecture-level risks:**
- **R1 — Document AI quality at the long tail of 25+ languages.** Eval-set authoring discipline is the only mitigation; the architecture exposes the provider abstraction so the team can swap or stack providers without a re-architecture.
- **R2 — RLS as the only isolation mechanism.** If RLS performance degrades at scale or a CVE surfaces, the v1 fallback is schema-per-tenant migration. The data layout is designed to survive that migration without an entity model change. [ADR-009](https://www.notion.so/36099f3e507f8116b7afe78e32d9a830).
- **R3 — Single-region active in v1.** A West Europe regional outage takes down all of Knauf's vetting. Mitigated by TTC's underlying multi-AZ posture on Postgres and Blob; multi-region passive is Phase 2.
- **R4 — Codegen pipeline introducing drift the test suite doesn't catch.** Drift-detection metrics on terminal-state distribution and envelope confidence are the early-warning surface; the self-healing pipeline subscribes and triggers re-evaluation specs. Coverage of the drift metric itself is the residual risk and is owned by the skills team.
- **R5 — ARC skill-lifecycle gates demoting Partner Vetting to degraded status without warning.** Mitigated by per-tool confidence monitoring and an alarm on the skill-status transition.
- **R6 — Counsel-gated launch (C7).** GDPR posture, consent semantics, liability framework, carve-outs all need sign-off before v1 ships. The architecture chose crypto-erasure to give counsel a clean GDPR story; the rest is contract negotiation.
---
## 14. Success metrics
Tied to QAs in §2.
**Leading (v1, first 90 days post-launch):**
- Automation rate (% of document checks resolved without human review). Target ≥ 80 %. Source: Result Envelope confidence distribution per check.
- Human-review queue p95 latency from enqueue → decision. Target ≤ 24 hours. Source: queue dwell-time histogram.
- p50 time-to-first-Coverage-Report for a partner with no prior validated artefacts. Target ≤ 6 minutes when no manual review fires. Source: Vetting Run duration histogram filtered to fully-automated terminal states.
- Document AI envelope confidence median per check. Target ≥ 0.85. Source: drift-detection event stream.
- Tool-level error rate at the MCP adapter. Target ≤ 0.5 % over rolling 7-day window. Source: OTel metrics.
**Lagging (v1, first 6 months post-launch):**
- Knauf vetted carrier count vs. Knauf carrier panel size. Target: a step-change improvement over Vera's 6 % ceiling — exact target set with Knauf in the v1 success-criteria workshop.
- Number of unique tenants on the platform. Target: Knauf at launch; ≥ 2 by month 6 (additional Trimble products as tenants).
- Cross-tenant Result Envelope reuse rate (% of Vetting Runs that satisfied at least one rule with an envelope produced under another tenant's run). Target: emerge from zero; track as a leading indicator of network effect.
- ARC skill-lifecycle status (% of v1 tool invocations served at `published` vs `degraded`). Target ≥ 99 %.
**Architectural health (continuous):**
- Drift signature firings per week on the drift-detection event stream. Target: \< 1 with no manual investigation outstanding.
- Codegen pipeline merge throughput (specs delivered → merged code per week). Target: TBD pending the v1 baseline.
- Audit completeness check (every state-changing handler in production traces emits ≥ 1 audit row). Target: 100 % — anything less is a build-failing bug.
---
## 15. Glossary
The glossary lives as a sub-page of this document for direct linking from other Notion pages. The inline canonical definitions are in §3 above; this sub-page mirrors them verbatim and is the linkable reference surface.
<page url="https://www.notion.so/36099f3e507f81d88961cb4e4a0b0118">Glossary</page>
---
## 16. Appendices — ADRs
Flat sub-pages of this document. Each ADR follows the same shape: Context · Decision · Rejected alternatives · Consequences.
**Note on tech-stack family ADRs (ADR-001 through ADR-015).** These are presented as **proposals** — current best directions to be confirmed by the engineer-review pass. Where a strong alternative exists (e.g. Go for the application runtime; React for the frontend; Datadog/Grafana/New Relic as observability backends), it is named in the ADR body. Final commitments land with review.
<page url="https://www.notion.so/36099f3e507f81aaa27cfe2562e72ce8">ADR-001 — Application language and runtime: TypeScript on Node.js LTS (proposed); Go a strong alternative</page>
<page url="https://www.notion.so/36099f3e507f81da9b86f9eb7ee6a564">ADR-002 — Primary OLTP store: PostgreSQL</page>
<page url="https://www.notion.so/36099f3e507f81faa265c252c886c9c4">ADR-003 — Document and object storage: Azure Blob</page>
<page url="https://www.notion.so/36099f3e507f81daa55ec3d9d137d8fc">ADR-004 — Search store: Postgres FTS (defer Elasticsearch)</page>
<page url="https://www.notion.so/36099f3e507f81e88b7fd468b3fd32f3">ADR-005 — Cache: Azure Cache for Redis</page>
<page url="https://www.notion.so/36099f3e507f81688f45d330feff3c6a">ADR-006 — Workflow orchestration: DB-backed state machine + Postgres outbox</page>
<page url="https://www.notion.so/36099f3e507f812ea099d603fcd44a0d">ADR-007 — Message bus: none in v1; Postgres outbox; Azure Service Bus deferred</page>
<page url="https://www.notion.so/36099f3e507f8181ba18fc11b03151e1">ADR-008 — Deployment topology: modular monolith</page>
<page url="https://www.notion.so/36099f3e507f8116b7afe78e32d9a830">ADR-009 — Tenant isolation: PostgreSQL row-level security</page>
<page url="https://www.notion.so/36099f3e507f81afae47d297eca8ae38">ADR-010 — Identity and programmatic surface: OIDC + Trimble ID; MCP-only external programmatic surface</page>
<page url="https://www.notion.so/36099f3e507f81dc91b4f2568493869e">ADR-011 — Observability stack: OpenTelemetry instrumentation (proposed); backend TBD by engineer review</page>
<page url="https://www.notion.so/36099f3e507f812789a0e26b23cca41b">ADR-012 — Frontend framework: Lit + Web Components (proposed); React + Web Components a strong alternative</page>
<page url="https://www.notion.so/36099f3e507f812f96bce468019ecbe7">ADR-013 — Document AI provider: Anthropic Claude with provider abstraction</page>
<page url="https://www.notion.so/36099f3e507f81e59156df776f8f15e5">ADR-014 — Testing framework family (proposed): backend + frontend coverage with named alternatives</page>
<page url="https://www.notion.so/36099f3e507f81b59021ccf8184d85d7">ADR-015 — Secret and key management: Azure Key Vault + per-profile Fernet envelope keys</page>
<page url="https://www.notion.so/36099f3e507f81a2bb24df59b34e9f0e">ADR-016 — Roles: Platform Admin, Tenant Admin, Tenant User, Partner</page>
<page url="https://www.notion.so/36099f3e507f81dd96dcc51c5fcba32d">ADR-017 — Consent model: per-(tenant, profile) opt-in grants, freeze-on-revoke</page>
<page url="https://www.notion.so/36099f3e507f812cac5dc1c72db615b5">ADR-018 — Cross-product propagation: Status Card embedding, no state replication</page>
<page url="https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50">ADR-019 — v1 UI delivery: standalone Partner Vetting Portal alongside embeddable Web Components</page>

### Glossary

The canonical terminology for Partner Vetting. Names in code match names in product match names in conversation (PCD §15, synthesis C11). Kept in sync with §3 of the Architecture Proposal by a CI check that diffs the two.
- **Partner** — any third party who can be the subject of a vetting workflow. v1 is restricted to carriers in logistics; the model is industry-agnostic by construction.
- **Profile** — the partner's vetting-specific record. Not a master record of the partner. Holds documents, validated results, workflow statuses, consent grants, and `external_ids[]` linking to canonical partner records elsewhere. Exactly one profile per partner across all tenants.
- **Document** — an artefact uploaded by a partner that substantiates one or more checks. Carries an expiration date where applicable. Subject to the *unique-purpose-per-slot* rule: a cargo insurance certificate cannot also occupy the company-registration slot. Documents are immutable after upload; the carrier replaces by uploading a new document, which versions the prior one.
- **Check** — a versioned, reusable primitive: one verifiable item with a defined input (document, profile attribute, or external query), a defined output (a typed Result Envelope), and a defined source of validation (external authority API, parser + cross-reference, or self-attestation). Platform Admins author checks; tenants do not.
- **Rule** — a predicate over a check's typed output payload plus a freshness window. `cargo_insurance.coverage_amount ≥ €1,000,000 AND cargo_insurance.expires_at > now() + 30d` is a rule.
- **Ruleset (= Vetting Workflow)** — a named, versioned bundle of rules defining what "vetted for purpose P" means for one tenant. Customer-facing term is **vetting workflow**; the internal term in code and audit events is **ruleset**. Tenants configure rulesets from the catalog; they do not author check primitives.
- **Vetting Run** — one execution of a ruleset against one profile. Carries `trigger_mode` (standing or at-engagement), `triggered_by` (subject and tenant), and `state` (running, awaiting_documents, awaiting_review, completed, expired). One Vetting Run produces zero-or-more Result Envelopes and exactly one Coverage Report at terminal state.
- **Result Envelope** — the typed per-check output of a Vetting Run. Wraps a check-specific extracted payload with metadata: `check_id`, `check_version`, `status ∈ {pass, fail, inconclusive}`, `confidence ∈ [0,1]`, `evidence_uri` (blob URL + content hash), `executed_at`, `valid_until`, `triggered_by`.
- **Coverage Report** — the per-Vetting-Run, per-rule classification emitted to the consumer. Each rule resolves to one of: `satisfied`, `missing`, `stale`, `version_downgraded`, `inconclusive`. There is no aggregate boolean.
- **Grant (= Consent Record)** — the partner's authorisation for a specific tenant to read specific sections of their profile. Grants are per-`(tenant, profile, section)`; default is opt-in. Revocation freezes future visibility but does not retroactively withdraw Coverage Reports already delivered.
- **Tenant** — an organisation that consumes Partner Vetting. v1 = Knauf. Trimble products that consume the service are tenants in their own right. v3+ external customers are tenants under their own IdP federation.
- **Role** — a user's permissions inside a tenant context (or the cross-tenant Platform Admin axis). Four roles in v1: Platform Admin, Tenant Admin, Tenant User, Partner. Role assignments are the only user-related data Partner Vetting stores; all user attributes come from the IdP per request.
- **Trigger mode** — Standing (periodic re-examination, partner-initiated, batch onboarding) or At-Engagement (just-in-time inside a host product's transactional flow, e.g. Marketplace bid acceptance). Both share the entire domain model; only the entry point and the default ruleset differ.
- **External IDs** — `(system, external_id)` pairs on Profile, Tenant, and Document pointing to canonical records elsewhere. Used to correlate, never to replicate.
- **Submission State** — the lifecycle state of one Vetting Run from the partner's perspective: `Pending`, `Missing`, `Approved`, `Rejected`, `Expired`. `Expired` is first-class and distinct from `Rejected`: it triggers automatic access-gating side effects in host products, and re-upload re-enters `Pending`.
- **Audit Event** — an immutable record of every state-changing operation. Append-only. Schema: `(event_id, occurred_at, tenant_id, actor_principal, on_behalf_of_user, action, entity_type, entity_id, before_state, after_state, evidence_uri?, cross_tenant)`.
- **Billable Event** — an immutable record of every commercially metered operation. Separate from audit because retention, consumers, and schema differ. Carrier-initiated vetting is not billable; tenant-initiated vetting is.
- **Notification / Alert** — outbound message to a partner or to a tenant operator about a state change. Transport is configurable per (tenant, recipient_class); v1 supports email and in-portal.
- **Platform Admin** — Trimble-internal role; stewards the Check catalog and authors standard rulesets; cross-tenant operations emit `cross_tenant=true` audit events.
- **Tenant Admin** — a user inside a tenant; configures rulesets, manages tenant users, views the Vetting Dashboard.
- **Tenant User** — a user inside a tenant; views vetting state on host-product surfaces.
- **Partner Submission Component** — `<pv-partner-submission>`. Lit-based Web Component embedded in carrier-facing hosts (Transporeon Registration Center in v1).
- **Status Card** — `<pv-status-card>`. Lit-based Web Component embedded *everywhere* a partner entity appears across Trimble products. Renders live state from Partner Vetting.
- **Workflow Configuration UI** — `<pv-workflow-config>`. Lit-based Web Component for Tenant Admins to configure rulesets.
- **Vetting Dashboard** — `<pv-vetting-dashboard>`. Lit-based Web Component for Tenant Admins and Tenant Users to view rollups.
- **MCP adapter** — the external programmatic surface (Mario, external customer agents). Sole external programmatic surface in v1 and v2.
- **Outbox** — Postgres table for at-least-once internal event delivery between bounded contexts. No external message bus in v1.
- **Bounded contexts** — Profile & Consent, Document Intake & Authentication, Rules, Network Signal (stub in v1).
- **TTC** — Trimble Transportation Cloud; the Azure-hosted internal platform that provides the catalog of services Partner Vetting runs on.
- **ARC** — Trimble's internal omnipotent AI agent platform; consumes Partner Vetting as a skill via MCP.
- **Mario** — the ARC agent end users interact with as a chat UI in Trimble products.
- **ARC-IP P1/P2/P3** — ARC integration patterns: P1 = Mario in ARC UI on behalf of Trimble-ID user; P2 = Trimble product calls ARC with application token + user identity; P3 = external product with user-scoped `arc_sk_` key.
- **ARC-SL** — ARC skill lifecycle: automated quality gates (draft → published; degraded if confidence drops). No manual review step.

### ADR-001 — Application language and runtime: TypeScript on Node.js LTS (proposed); Go a strong alternative

**Status: Proposed — subject to engineer review.** This ADR commits to a categorical direction, not a final library set. The two serious candidates are TypeScript on Node.js LTS and Go. The trade-off has more to do with team familiarity and existing Trimble runtime expertise than with abstract codegen scoring.
## Context
Every line of the Partner Vetting implementation will be produced by autonomous AI codegen. The team is six non-engineers and the v1 deadline is two months. The architecture imposes typed contracts at every boundary (§9.1) and exhaustive automated tests as the sole quality gate. The language and runtime choice has the largest single effect on the codegen pipeline's reliability: it sets the static-type density, the LSP feedback loop tightness, the testing-tool ecosystem, and the size of the training corpus the codegen sampled from.
This decision is *categorical* — TypeScript versus Python versus Go versus Rust versus Kotlin/Java. Specific framework choices (HTTP server, ORM, build tool) belong to the design doc.
## Decision (proposed)
**TypeScript on Node.js LTS as the proposed primary.** Single language across backend service, MCP adapter, Web Components, and shared schema/type generation.
**Go is a strong alternative** and should not be ruled out at the engineer-review pass — particularly if the team includes engineers with significant Go experience or if Trimble's existing TTC-hosted services skew Go-native.
## Why TypeScript / Node.js LTS
- One language for the entire stack — schemas, server, MCP adapter, Web Components, tests, and codegen specifications.
- Branded types (`Email`, `Token`, `TenantId`) carry the no-PII-in-logs and tenant-isolation lint rules.
- Large LLM training corpus → predictable codegen output.
- Mature LSP feedback loop accelerates the spec-pipeline iteration.
- Node.js LTS gives a predictable runtime; the analysis worker pool runs as separate Node processes inside the same container.
## Why Go is a serious candidate
- Stability patterns (context, timeouts, circuit breakers, bulkheads) are idiomatic, not library-bolted-on. Codegen is more likely to land them correctly.
- Deterministic builds and single-binary deployments simplify the deploy story.
- Strong runtime performance ceiling if any Phase-2 workload turns CPU-bound (document AI pre/post-processing, signature verification at scale).
- If Trimble's existing TTC-hosted services are predominantly Go, team operational familiarity weighs more heavily than codegen-corpus size.
- Codegen quality on idiomatic Go is acceptable, and the language's small surface limits the failure modes codegen can introduce.
## Rejected alternatives
- **Python.** Largest training corpus and strong document-AI ecosystem, but type checking is opt-in (mypy/Pyright are bolt-on), runtime is interpreted with weaker deterministic-build guarantees, and the team would need a separate frontend stack — splitting the codegen target across two languages doubles the contract surface the spec pipeline must respect.
- **Rust.** Best correctness story; not viable for codegen velocity inside a two-month window with non-engineers.
- **Kotlin / Java.** Excellent type density and JVM ecosystem; codegen quality on idiomatic Kotlin is uneven, and a JVM stack would split the frontend.
## How to decide between TypeScript and Go
The engineer-review pass should answer:
1. **Team skill mix.** How many of the engineers shipping v1 are TS-native vs Go-native? Codegen-friendly languages without team familiarity for review and integration debugging is a real risk.
2. **TTC runtime mix.** What does Trimble's existing operational discipline support best — npm-class supply chain or Go-module supply chain?
3. **Frontend strategy.** If [ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b) lands on React or Lit (both TS-native), TypeScript on the backend keeps the stack single-language. If the frontend goes another direction, that argument weakens.
4. **CPU-bound headroom.** Does the v1 workload have any hot path that Node's single-threaded model strains? If yes, Go is the safer pick.
## Consequences
- The architecture commits to *a single language family* across backend, MCP adapter, and (if TypeScript) the frontend. Mixed languages are explicitly off the table for v1.
- Library choice (HTTP server, ORM, schema validation) is a design-doc decision; the architecture commits only to the language and runtime family.
- If the engineer-review pass flips this ADR to Go, the changes downstream are scoped: the testing framework family ([ADR-014](https://www.notion.so/36099f3e507f81e59156df776f8f15e5)) shifts from Vitest/fast-check/Pact toward Go-native equivalents (testing + testify + property-testing libraries + Pact-go), and the Web Components ADR ([ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b)) decouples from this ADR — Lit-vs-React doesn't depend on the backend language.

### ADR-002 — Primary OLTP store: PostgreSQL

## Context
The Partner Vetting domain is entity-heavy and referentially dense: Partner ↔ Profile ↔ Document ↔ Result Envelope ↔ Vetting Run ↔ Coverage Report ↔ Ruleset ↔ Check ↔ Grant. The data architecture (§7) requires:
- Strong referential integrity across the entity graph
- Tenant isolation as a hard architectural property (§7.5)
- Append-only audit and billable event streams (§9.3)
- A durable, transactionally consistent job queue for the analysis worker pool (§6.2)
- An outbox pattern for in-process at-least-once event delivery between contexts (§6.5)
- JSON columns for the heterogeneous Result Envelope payloads and Check predicate ASTs
The TTC catalog provides Postgres (Azure Database for PostgreSQL Flexible Server), MongoDB, and other options. The choice is the primary OLTP family.
## Decision
**PostgreSQL** (Azure Database for PostgreSQL Flexible Server, single instance v1, with point-in-time backup and a read replica for analytics).
## Rejected alternatives
- **MongoDB.** Excellent for unbounded-schema document storage. The Partner Vetting domain is the opposite — schemas are tight, relationships are critical, and ACID transactions across the outbox + entity tables are load-bearing. The Result Envelope is the one entity where document-store ergonomics would help; it fits in a JSONB column on Postgres with no architectural penalty.
- **CockroachDB / distributed SQL.** Solves problems v1 does not have (horizontal scale, global distribution) at the cost of feature lag against Postgres (notably RLS support is recent and less battle-tested in CRDB).
- **MySQL / MariaDB.** Comparable to Postgres on many dimensions; loses on RLS maturity, JSONB ergonomics, and PostGIS-class extensions if Phase 2 wants geography-keyed queries.
- **Document-store-plus-SQL hybrid (e.g., Mongo + Postgres).** Two persistence families doubles the codegen contract surface, doubles the migration tooling, doubles the backup discipline. Not worth it for the JSONB ergonomics gap.
## Consequences
- Tenant isolation enforced via PostgreSQL row-level security ([ADR-009](#)).
- The outbox table, the analysis job queue (`FOR UPDATE SKIP LOCKED`), and the durable state machine for Vetting Run all live in Postgres — no separate broker or workflow engine ([ADR-006](#), [ADR-007](#)).
- Result Envelope payloads and Check predicate ASTs use JSONB columns with schema validation enforced in the application layer.
- Backup is point-in-time recovery (7-day window v1); soft-delete on Blob mirrors the same window.
- The design doc covers index strategy, partitioning on `audit_events` and `billable_events` (by month), and the migration path to schema-per-tenant if RLS performance degrades (the contingency in [ADR-009](#)).

### ADR-003 — Document and object storage: Azure Blob

## Context
Partner Vetting accepts documents in 25+ languages (LR §«Multilingual Document Processing») from carriers across Europe and, in Phase 2, North America. Documents are immutable after upload, evidence-linked from Result Envelopes via content hash, lifecycle-managed (hot/cool/archive), and subject to GDPR crypto-erasure via per-profile envelope keys ([ADR-015](#)).
The TTC catalog provides Azure Blob Storage. The choice is whether to use it and how to integrate.
## Decision
**Azure Blob Storage**, with:
- One container per environment, prefixed by `tenant_id` for storage-level audit clarity and to allow per-tenant lifecycle overrides where contract requires it.
- Document records persisted in Postgres carry `(blob_uri, content_hash, mime, content_length, uploaded_at)`; raw bytes live only in Blob.
- **Application-layer envelope encryption** with per-profile keys in Key Vault. Blob's server-side encryption (Azure-managed keys) is the underlying layer; envelope encryption adds the GDPR crypto-erasure mechanism on top.
- **Lifecycle rules**: hot tier 0–90 days, cool tier 90–365 days, archive tier 365+ days. Aligned with audit retention.
- **Soft-delete** enabled with a 30-day window so accidental deletes are recoverable.
## Rejected alternatives
- **Postgres ****`bytea`**** columns.** Acceptable up to ~10 MB per row; vetting documents (insurance certificates with scanned attachments, multi-page PDFs) routinely exceed this. Doubles backup cost. Loses lifecycle tiering.
- **S3 / non-Azure object store.** Outside the TTC catalog; would require its own credential and audit posture without benefit.
- **Filesystem on persistent volumes.** Tied to instance topology; no lifecycle management; harder to clone for staging.
## Consequences
- The Document Store Adapter (§6.1) is the only component that talks to Blob. Other contexts reference documents through Profile & Consent's typed interface.
- Content hash is computed on upload and persisted alongside the Blob URI; cross-tenant or cross-profile reuse of a previously-uploaded document is *possible* in principle (same content, different upload event) but explicitly *not* permitted in v1 because each document upload event is the consent-bearing artefact for the uploading profile.
- Envelope encryption adds a constant overhead per read; the IdP-attribute and rate-limit caches do not touch this path, so the hot read path is unaffected.
- The design doc covers Blob container layout, lifecycle rule definitions, CMK options for high-compliance tenants, and the back-pressure model when Blob ingress is rate-limited.

### ADR-004 — Search store: Postgres FTS (defer Elasticsearch)

## Context
v1 surfaces with search-shaped needs:
- The Workflow Configuration UI needs to find checks in the catalog (~40 entries at launch, growing slowly).
- The Vetting Dashboard needs to filter Vetting Runs by tenant, ruleset, partner, state, and date range.
- Operators in the human review queue need to search by partner name, country, and submission age.
These are small-cardinality, indexable, primarily-relational queries with light free-text needs (partner name, document slot).
## Decision
**PostgreSQL full-text search** (built-in `tsvector` / `tsquery`), with B-tree and GIN indexes on the few free-text columns that matter.
Defer Elasticsearch (or any external search store) to Phase 2 or later, gated on a concrete need: tenant-facing catalog browsing across millions of partners, or fuzzy multilingual search across partner directories.
## Rejected alternatives
- **Elasticsearch from v1.** Adds a second persistence family, a sync pipeline, an operational discipline (cluster sizing, JVM tuning), and a backup story. None of v1's queries justify it.
- **Azure AI Search.** Strong for full-text + vector hybrid; same complexity argument as Elasticsearch for v1, and would tie the search layer to Azure prematurely.
- **In-memory search (loki-class).** Doesn't survive process restart; not a real alternative for the Dashboard's persistent filter use case.
## Consequences
- The v1 query layer is one Postgres connection pool. No cross-store consistency to engineer.
- The Phase-2 migration path (if needed): introduce Elasticsearch behind a typed search-interface that v1 already pins (`SearchService.find_partners(query, filters) → Page<Partner>`), so the swap is a single implementation, not an architecture change.
- The design doc covers index strategy (`tsvector` columns, `GIN` indexes), query-shape catalogue, and the dashboard's pagination model.

### ADR-005 — Cache: Azure Cache for Redis

## Context
Three cache shapes exist in v1:
- **IdP attribute cache** — user attributes resolved from Trimble ID userinfo on cache miss; needed because Partner Vetting stores no user records (PCD §10, synthesis C9). Hot path; p95 ≤ 150 ms target (§2).
- **Rate-limit counters** — token-bucket per `(auth_principal, tenant)` at the MCP adapter and the internal HTTP boundary. Default 60 RPM with per-skill overrides (§9.5, synthesis Q11).
- **Integration response cache** — short-lived caches for FMCSA, VAT registry, and similar external authoritative source responses where the source supports it.
All three need: low single-digit-millisecond latency, expiry semantics, and per-key TTLs.
## Decision
**Azure Cache for Redis** (TTC catalog). Single instance v1; standard tier with replication.
- IdP attribute cache TTL: 5 minutes.
- Rate-limit counters: per-token-bucket; 60-second window default.
- Integration response cache: per-source TTL configured in the integration record.
## Rejected alternatives
- **In-process LRU cache.** Doesn't share state across the API process, the outbox worker, and the analysis workers. IdP attribute cache misses would multiply by process count.
- **Postgres as cache.** Latency floor (~5 ms on Azure Postgres) is order-of-magnitude above what the IdP hot path needs; also burns connection pool entries.
- **Memcached.** Comparable to Redis on the simple-cache axis; loses on the rate-limit data structures (Redis's atomic increment + expiry is the canonical pattern).
## Consequences
- The cache layer is a soft dependency: a Redis outage degrades performance (more Trimble ID userinfo calls, looser rate-limit enforcement) but does not break correctness. The circuit-breaker on Redis falls back to direct Trimble ID lookups and a conservative rate-limit posture (in-process counter, lower default).
- The design doc covers Redis cluster sizing, persistence settings (we use Redis as a cache — RDB snapshots not required), and the rate-limit data-structure shape.

### ADR-006 — Workflow orchestration: DB-backed state machine + Postgres outbox

## Context
The Vetting Run is a durable, multi-step state machine: `created → running → awaiting_documents → running → awaiting_review → running → completed`. Transitions are driven by external events (document upload, document AI extraction completion, human review decision, wall-clock expiry). Runs must survive process restarts, container redeploys, and partial failures.
The Submission state machine (§7.2) layers on top: Pending, Missing, Approved, Rejected, Expired.
Document Intake additionally needs:
- A durable analysis job queue with at-least-once delivery to worker processes.
- A retry budget (3 attempts per LR §«Retry and HITL Escalation Contract»).
- Escalation routing to the human review queue on retry exhaustion.
The choice is between three orchestration families: a DB-backed state machine (Postgres-only), a Temporal-class workflow engine, or event-driven choreography over a message bus.
## Decision
**Postgres-backed durable state machine + outbox table for in-process at-least-once event delivery between contexts.** Specifically:
- Vetting Run state persisted in Postgres; transitions are SQL updates inside transactions that also emit outbox events.
- Analysis job queue: a `analysis_jobs` table consumed by workers via `FOR UPDATE SKIP LOCKED`. Retry counter on the row; failure routes to the human review queue.
- Outbox emitter writes domain events into an `outbox` table inside the same transaction as the entity write; a background worker reads the outbox in commit order, dispatches to in-process subscribers (audit, billable, notification), marks rows delivered.
- Scheduled re-examination (6–8 month window per LR §«Validation Validity Window») and per-document expiry sweep: a `scheduled_tasks` table consumed by a cron-like worker.
## Rejected alternatives
- **Temporal (or **[**temporal.io**](http://temporal.io)**-class engine).** Excellent durability and replay semantics; battle-tested. Adds a second persistence family (Temporal's own backing store), an operational discipline, and a contract surface (workflow versioning, signal protocols) that the codegen pipeline would need to model separately. The Vetting Run state machine is bounded (≤ 8 states, ≤ 12 transitions); the cost of Temporal isn't paid back in v1 complexity reduction.
- **Event-driven choreography over Kafka / Service Bus.** See [ADR-007](#) — no external bus in v1. Choreography over Postgres outbox achieves the same in-process at-least-once semantics without the operational cost.
- **In-memory orchestration (process-resident).** Cannot survive a redeploy; fails the durability requirement.
## Consequences
- One persistence family for state, jobs, outbox, and entities. Backup posture is unified.
- The state machine is a typed TypeScript module enforced by lint rules: state transitions must call a single `transition(run_id, from, to, evidence?)` function that writes both the new state and the outbox event in one transaction.
- The trade-off: Postgres has to absorb the throughput of state-machine traffic. Capacity calculations (which the design doc owns) need to validate that v1's expected vetting volume (worst-case Knauf onboarding + Vera replacement traffic) stays inside the single-instance Postgres envelope. The contingency is partitioning the high-throughput tables (audit, billable, outbox) by month — already part of [ADR-002](#)'s steady-state plan.
- If a future tenant onboarding pushes orchestration complexity beyond what the DB-backed state machine handles gracefully (long-running multi-day workflows with complex compensation), the migration to Temporal becomes a Phase-3 ADR. The Vetting Run shape is small enough that this is unlikely before Phase 3.

### ADR-007 — Message bus: none in v1; Postgres outbox; Azure Service Bus deferred

## Context
The synthesis flags event-driven architecture as an explicit open question (Q13) — whether a message bus such as Kafka or Azure Service Bus belongs in the architecture. The decision interacts with:
- The deployment topology ([ADR-008](#)) — modular monolith vs. service decomposition vs. event-driven services.
- The workflow orchestration choice ([ADR-006](#)).
- The cross-product propagation story ([ADR-018](#)) — how a Vetting Run outcome reaches other Trimble products.
## Decision
**No external message bus in v1.** Internal context-to-context event delivery uses a Postgres outbox table with at-least-once semantics. The four bounded contexts share one process; cross-context calls are typed in-process function calls; cross-context events are outbox emissions consumed by an in-process worker.
**Azure Service Bus** is the reserved Phase-2 option from the TTC catalog if and when cross-product propagation requires fanout beyond what HTTP pulls from other Trimble products can serve.
## Rejected alternatives
- **Kafka in v1.** Operational discipline (cluster sizing, partition strategy, schema registry) is not justified by v1's load. Cross-product fanout doesn't exist in v1 (Knauf is the only tenant; other Trimble products are not yet onboarded). Adds a third persistence family (Kafka's own log) and a codegen contract surface (consumer group semantics, partition keys, exactly-once posture).
- **Azure Service Bus in v1.** Smaller operational footprint than Kafka; same justification gap. The Postgres outbox already gives at-least-once internal delivery with one persistence family.
- **HTTP webhooks for cross-product propagation.** Considered for Phase 2 fanout; the architecture intentionally doesn't decide between Service Bus and webhooks now — the decision lands when Phase 2 surfaces a concrete consumer with a contract.
## Consequences
- One persistence family for state, jobs, outbox, and entities.
- The outbox emitter is the single integration point for downstream event consumers — audit, billable, notification. Adding a fourth in-process subscriber (e.g., a search-index updater in Phase 2) requires no new infrastructure.
- The cost of the Phase-2 migration to Service Bus, when it happens: outbox events are already typed contracts. The Service Bus adapter becomes an additional outbox subscriber that fans out to the bus. The contract doesn't change.
- The risk: if Phase 2 surfaces an unexpectedly large cross-product fanout (e.g., five Trimble products each subscribing to every Vetting Run completion), the outbox-pull model could strain the database. Mitigation: the outbox-to-bus adapter ships ahead of mass onboarding, and the fan-out moves to Service Bus.

### ADR-008 — Deployment topology: modular monolith

## Context
The synthesis flags deployment topology as OPEN (§6, cross-check `v1-architecture-modular-monolith`). The three families on the table:
- **Modular monolith** — single deployable, multiple bounded contexts as enforced module boundaries.
- **Service decomposition** — one service per bounded context, communicating over HTTP or message bus.
- **Event-driven services** — services communicating asynchronously over a message bus, no direct HTTP calls between them.
Constraints that bear on the decision:
- C1 — fully autonomous AI codegen; every line spec-driven; no human PRs.
- C3 — ~2-month v1 timeline.
- C6 — TTC platform substrate (Azure).
- Six-person team, none of whom are software engineers by background.
- Four bounded contexts: Profile & Consent, Document Intake & Authentication, Rules, Network Signal (stub).
## Decision
**Modular monolith.** Single TTC service. Four bounded contexts as enforced module boundaries (import-linter rules; cross-context imports outside the published context interface fail CI). Multiple processes inside one container: API process, outbox worker, analysis worker pool, scheduled-task worker.
## Rejected alternatives
- **Service decomposition (one service per context).** Four services means four CI/CD pipelines, four observability surfaces to wire, four sets of TTC resources to provision, four boundaries to authenticate. The codegen pipeline becomes responsible for keeping four separate type contracts in sync where one in-process type contract suffices. The autonomous-codegen + 2-month + non-engineer-team combination is what tips the scale: distributed-systems engineering is the hardest thing for codegen to get right without human oversight. The contexts share enough referential integrity (Profile ↔ Vetting Run ↔ Result Envelope ↔ Coverage Report) that the network cost of separating them isn't paid back.
- **Event-driven services.** Same cost as service decomposition plus a message bus ([ADR-007](#)) plus eventual-consistency reasoning across every cross-context call. The Vetting Run is a strongly-consistent state machine — eventual consistency is the wrong default for v1's domain.
- **A single process with no module boundaries (pure monolith).** Loses the v1 architectural property that contexts are independently reasoned about and independently testable. The import-linter rules cost is small; the discipline payback (clean Phase-2 extraction if a context outgrows the monolith) is large.
## Consequences
- One deployable; one CI/CD pipeline; one observability surface; one tenant-isolation boundary (RLS); one Postgres connection pool.
- Cross-context calls are typed function calls; the lint rule that forbids reaching past the published interface enforces the bounded-context discipline that *would* be enforced by network boundaries in a distributed deployment.
- The Phase-2 extraction path (if any context outgrows the monolith — most likely Document Intake's analysis worker pool) is: extract the worker pool as a separate service behind the existing in-process interface. The in-process boundary becomes a typed HTTP boundary; Pact tests are already in place because the same interface was contract-tested at the in-process layer.
- The risk: the autonomous-codegen pipeline produces code that violates context boundaries by reaching past the published interface. Mitigation: import-linter rules in CI; review on every spec-produced merge that the linter passed. The architecture does not require a human review step on merge — it requires that the linter step is gating, and that the lint rules themselves are spec-driven.

### ADR-009 — Tenant isolation: PostgreSQL row-level security

## Context
C8 — multi-tenancy from v1 — requires hard isolation between tenants even though Knauf is the only tenant at launch (PCD §12). Onboarding tenant N+1 must be a configuration exercise, not a re-build. The isolation mechanism is a categorical architectural choice (synthesis §9.3, §7 Q12, §8 G8).
Four mechanism families:
- **Row-level security (RLS)** in Postgres — every tenant-scoped table carries a `tenant_id`; policy filters every query against a per-request session variable.
- **Schema-per-tenant** — one Postgres schema per tenant; the application binds to the right schema at connection acquisition.
- **App-layer scoping** — every query carries an explicit `tenant_id` filter; correctness relies on application discipline alone.
- **Database-per-tenant** — full physical separation.
## Decision
**PostgreSQL row-level security.** Every tenant-scoped table carries a `tenant_id` column with an RLS policy keyed off a per-request session GUC (`pv.current_tenant`) and a Platform-Admin escalation GUC (`pv.current_principal_role`). The application's per-request middleware sets both GUCs at connection acquisition; the GUCs reset on connection release.
Pattern:
```sql
CREATE POLICY tenant_isolation ON <table>
  USING (
    tenant_id = current_setting('pv.current_tenant')::uuid
    OR current_setting('pv.current_principal_role') = 'platform_admin'
  );
```
Cross-tenant queries (Platform Admin only) emit `audit_events` with `cross_tenant=true`.
## Rejected alternatives
- **Schema-per-tenant.** Strong physical isolation; high operational cost in v1 (multi-tenant schema migrations are a real chore — every schema needs every migration, in order, with rollback). Loses cross-tenant queryability for legitimate Platform-Admin paths (catalog stewardship, network-reuse statistics). Re-introduce as a Phase-2 contingency only if RLS performance degrades or a CVE surfaces.
- **App-layer scoping only.** Correctness relies on application discipline; one missed filter is a tenant-cross. The codegen pipeline producing the queries is exactly the wrong correctness model for app-layer scoping — *one* unaudited change leaks.
- **Database-per-tenant.** Cleanest isolation; un-economical for v1 (one tenant) and Phase 2 (a handful of tenants). Re-evaluable in Phase 3 for high-compliance external customers.
## Consequences
- Tenant isolation is enforced at the database layer. Application bugs that forget a tenant filter still fail closed: the RLS policy denies the row.
- Integration tests assert the RLS denial path on every tenant-scoped table.
- Platform Admin escalation is a privileged path: the role assignment is checked at middleware entry; the GUC is set; every operation under that GUC emits a `cross_tenant=true` audit event. Audit consumers (Applied AI Safety & Enablements) can filter to this surface for review.
- The migration path to schema-per-tenant if RLS performance degrades: the entity model is unchanged (each table still carries `tenant_id`); the migration replaces the RLS policy with a per-schema partition and the middleware switches the session schema instead of the GUC. The codegen contract doesn't change.
- The cost: RLS adds a small per-query overhead. The dashboard's analytic queries (cross-tenant rollups for Platform Admins) bypass via the escalation GUC and are isolated to a read replica.

### ADR-010 — Identity and programmatic surface: OIDC + Trimble ID; MCP-only external programmatic surface

## Context
Two coupled decisions:
1. **Identity stack.** Partner Vetting stores no user records (synthesis C9, PCD §10). Authentication and user-attribute resolution federates entirely to external IdPs — Trimble ID in v1, customer IdPs in Phase 3. The library family for OIDC token validation and resource-server authorisation is a categorical choice.
2. **Programmatic surface.** The synthesis cross-check (§6) marks the wiki's `mcp-only-programmatic-surface` as DIFFER because the PCD names APIs *and* MCP *and* web components as three distinct consumption surfaces (PCD §9). Q8 is the explicit open question: is there a REST/HTTP API surface alongside MCP, or is MCP the only programmatic surface?
The two decisions interact: the same token validation stack must serve every authenticated path — MCP, internal HTTP, REST if any.
## Decision
**Identity:** OAuth 2.0 / OIDC, primary IdP Trimble ID. Library family: `jose`-class for JWT/JWS validation, `Authlib`-class on the resource server side. ARC integration patterns P1 (Mario in ARC UI on behalf of Trimble-ID user), P2 (Trimble product calls ARC with application token + user identity), P3 (external product with user-scoped `arc_sk_` key) are adopted as-is. End-user identity propagates through agent calls via a structured `actor.on_behalf_of_user` parameter on every tool that operates on user-scoped state (synthesis Q10).
**Programmatic surface:** **MCP is the sole external programmatic surface in v1 and v2.** No public REST API. The internal HTTP boundary between Web Components and the service layer is private — not documented publicly, not addressable from outside, never exposed to external customers.
Reasoning:
- One published programmatic surface keeps the documentation and codegen contract surfaces minimal. ARC-IP P3 already supports external-customer-agent invocations.
- Web Components handle every UI case. Programmatic cases land on MCP.
- ARC's skill-lifecycle gates (ARC-SL) give automated quality control on the MCP surface that a REST API would have to re-implement.
- The DIFFER in synthesis §6 is on the "ever" framing — Phase 3 reevaluates if a concrete external customer surfaces a REST requirement, but v1 and v2 don't.
## Rejected alternatives
- **REST + MCP in parallel in v1.** Doubles the published surface; doubles the contract testing; doubles the documentation pipeline. The ARC-SL automated quality gates don't extend to REST. No v1 caller asks for it.
- **REST in front of MCP (REST as the canonical surface, MCP wrapping REST).** Inverts the ARC integration story — Mario calls MCP first-class; routing it through a REST adapter adds a hop without payback.
- **MCP wrapping REST (REST canonical, MCP is a façade).** Same cost as the REST+MCP option, plus the façade's translation layer needs codegen attention every time the tool surface changes.
- **gRPC.** Considered for the internal HTTP boundary; loses on debuggability and on the JSON-Schema source-of-truth posture the architecture already commits to.
- **Custom IdP code.** Token validation is a security primitive; rolling it is the wrong category for codegen.
## Consequences
- The MCP surface (§8.1) is the published programmatic contract: 13 tools at v1, each with a typed input/output schema, subject to ARC-SL automated quality gates.
- Per-request middleware does token validation once and binds the resolved `(principal, tenant, role)` to the connection — used by both the MCP adapter and the internal HTTP layer.
- The Phase-3 trigger for revisiting: a paying external customer with a concrete REST requirement. The migration path: the existing MCP tool surface is exposed as REST via a generated adapter (every MCP tool has a JSON-Schema input/output already; the REST shape falls out trivially). The internal service contract is unchanged.
- The risk: a tenant insists on REST in Phase 2. Mitigation: re-open this ADR; the migration is mechanical, not architectural.

### ADR-011 — Observability stack: OpenTelemetry instrumentation (proposed); backend TBD by engineer review

**Status: Proposed — subject to engineer review.** The instrumentation library (OpenTelemetry) is a categorical decision that should hold regardless of the backend choice. The observability *backend* — where traces, metrics, and logs are aggregated, queried, and alerted on — is a separate decision with multiple viable candidates inside Trimble's toolkit. This ADR proposes a direction and names the trade-offs; final backend pick belongs to the engineer-review pass.
## Context
Autonomous codegen as the build mechanism (C1) makes observability load-bearing in a way it isn't for human-engineered systems: there are no humans reading PRs or watching for regressions. Drift in production behaviour has to surface to the self-healing pipeline through telemetry, not through a human noticing.
Three observability pillars matter equally:
- **Traces** — span per MCP tool invocation, per internal HTTP request, per outbox dispatch, per external integration call.
- **Metrics** — golden signals per tool and per integration; per-check `(envelope_confidence, latency_ms)` histograms; per-Vetting-Run terminal-state distribution; queue depth.
- **Logs** — structured JSON; no PII; correlation id on every line.
Plus a drift-detection event stream that the self-healing pipeline subscribes to.
Two distinct decisions are involved:
1. **Instrumentation library** — what the application code calls to record telemetry. Vendor-neutral if chosen well; portable across backends.
2. **Backend** — where the telemetry lands, is stored, queried, and alerted on. Vendor-specific by nature.
The architecture should commit to (1) and leave (2) as a separate, swappable choice.
## Decision (proposed)
**OpenTelemetry SDK across all signals** (traces, metrics, logs). Vendor-neutral instrumentation is a hard architectural commitment — the backend is interchangeable behind the same SDK.
**Backend: deferred to engineer review.** Multiple candidates from Trimble's available toolkit, all viable behind the same OTel instrumentation:
- **Datadog** — strong unified UI, mature integration catalogue, used at multiple Trimble teams.
- **Grafana Cloud or self-hosted Grafana + Prometheus + Loki + Tempo** — open-source baseline; full control; lower per-unit cost at scale; more operational lift if self-hosted.
- **New Relic** — strong APM + traces; already in use in parts of Trimble.
- **Azure Monitor** — TTC catalogue default; tight integration with the rest of the Azure runtime; lower friction at deploy time.
Each is a viable target for the same OTel instrumentation. The architecture commits to neither.
## Why OTel is the proposed instrumentation choice
- **Vendor neutrality.** Application code calls OTel; the backend is configured by exporter. Swapping Datadog → Grafana → New Relic is a deploy-time configuration change, not a re-instrumentation exercise.
- **Cross-process trace propagation.** Trace context propagates across the MCP adapter, the internal HTTP boundary, the outbox dispatcher, and external integration calls without custom plumbing.
- **Codegen-friendly.** OTel's API is broadly trained in the LLM corpus; codegen output is predictable.
- **Industry standard.** OTel is the convergence point for the observability ecosystem; betting on it minimises long-term churn.
## How to decide the backend
The engineer-review pass should weigh:
1. **Existing Trimble standardisation.** Does TTC, Marketplace, or the broader Trimble engineering org already standardise on one of the four? Operational alignment with that choice removes a friction layer.
2. **Cost model at v1 scale.** v1 volume is small. Datadog's per-host pricing is steep; Azure Monitor is cheaper for small deployments; Grafana self-hosted is cheapest at scale but has operational lift.
3. **Alerting and SRE tooling.** Which backend's alerting model and dashboard ergonomics match how the on-call/self-healing pipeline will consume signals?
4. **Drift-detection consumer.** The self-healing pipeline subscribes to the drift-detection event stream (§9.1). Backend choice affects how that consumer integrates — Azure Monitor's Log Analytics, Datadog's Logs API, or a custom Prometheus exporter all work, but the integration code differs.
## Rejected alternatives (instrumentation)
- **Vendor-specific SDK (Datadog ****`dd-trace`****, New Relic agent, Azure Monitor SDK).** Better ergonomics in one backend; loses portability. Committing to vendor-specific instrumentation makes future backend swaps a re-instrumentation exercise. OTel is the vendor-neutral substrate and is broadly accepted.
- **Logs-only / no structured tracing or metrics.** Fails the codegen-first requirement: drift detection needs metrics, traces correlate state-machine transitions across processes.
- **Custom in-house telemetry library.** No payoff; OTel covers every case the architecture needs.
## Consequences
- One instrumentation library across backend, MCP adapter, and (where instrumentable) frontend.
- The metric and log naming conventions are committed in the design doc; codegen reads them as the contract.
- Backend swap is a configuration exercise (OTel exporter swap), not a re-instrumentation.
- If the v1 backend pick later turns out wrong (cost overrun, missing capability, vendor risk), the architecture survives the swap without changing application code.
- The drift-detection event stream's consumer interface is defined against OTel's data model, not a specific backend's data model — same swap-friendliness applies.

### ADR-012 — Frontend framework: Lit + Web Components (proposed); React + Web Components a strong alternative

**Status: Proposed — subject to engineer review.** Lit is the proposed primary because of framework-agnostic embedding and bundle weight. React is a strong alternative, and the introduction of the standalone Partner Vetting Portal in v1 ([ADR-019](https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50)) shifts the trade-off in React's favour for teams already standardised on React. Final pick belongs to the engineer-review pass.
## Context
The Web Component family ships into two host environments:
1. **v1 — the standalone Partner Vetting Portal** ([ADR-019](https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50)). A single TTC-hosted single-page app that mounts all five components under one login. The portal is a controlled environment — whatever framework the components use, the portal uses too.
2. **Phase 2 — embedded in other Trimble products.** Trimble Marketplace (React), TMS family surfaces (some Angular, some other), Transporeon Registration Center (carrier-facing), and a v3+ standalone host for external customers. The mix is mostly React-dominant with some Angular and vanilla.
The five-component family:
- `<pv-status-card>` — embedded everywhere a partner entity appears; bundle weight matters.
- `<pv-workflow-config>` — admin surface; bigger; lower frequency.
- `<pv-vetting-dashboard>` — admin surface.
- `<pv-partner-submission>` — partner-facing active write flow for one Vetting Run.
- `<pv-partner-profile>` — partner-facing home view (profile summary, document library, vetting history across tenants, shipper-connection and grant management, active vs saved state).
Synthesis flags:
- **Q20** — framework-agnostic Web Components vs. React micro-frontends vs. hybrid.
- **Q18** — pre-built fixed components vs. dynamic generation (resolved: fixed parameterised; dynamic deferred).
## Decision (proposed)
**Proposed primary: Lit (TypeScript) producing framework-agnostic Custom Elements.** Same components are mounted by the Partner Vetting Portal in v1 and embedded in other Trimble products in Phase 2.
**Strong alternative: React 19+, exposing Custom Elements via React's native web component support.**
Fixed parameterised components in v1 (dynamic generation deferred).
## Why Lit (the proposed primary)
- **Framework-agnostic by default.** Custom Elements work in React, Angular, Vue, and vanilla hosts without runtime conflicts. The Phase-2 embedding scenario into Angular TMS surfaces is materially smoother with Lit than with React-as-host.
- **Smaller bundle.** Lit's runtime is ~5 KB. React + react-dom is ~40 KB. For the `<pv-status-card>` embed-everywhere case, weight matters.
- **Codegen-friendly idioms.** Lit's reactive update model + typed templates + decorators give the codegen pipeline a high-leverage target to generate against.
- **First-class in browser standards.** Custom Elements are a native browser primitive; the path is forward-compatible without depending on one library's roadmap.
## Why React is a serious candidate
- **Trimble team expertise.** React is the dominant frontend at Trimble. Codegen quality on React is at least as good as on Lit, and the team's debugging/extending skill is much higher.
- **React 19's native Web Components support.** The historical "React doesn't talk to Custom Elements cleanly" problem is much smaller in React 19. The framework-agnostic-embedding argument for Lit has narrowed.
- **The v1 portal is React-friendly.** With [ADR-019](https://www.notion.so/36099f3e507f81f8aa66e2a7ddd6bc50) shipping a standalone portal as the v1 surface, the host *is* React-native. Lit's "ship anywhere" property doesn't get exercised in v1.
- **Marketplace (React-native) is the largest Phase-2 embedding target.** If the embedding surface turns out to be heavily React-skewed, React-native components avoid an adapter layer.
- **Larger training corpus.** Codegen reliability on React patterns is significantly higher than on Lit.
## How to decide between Lit and React
The engineer-review pass should answer:
1. **What is the actual Phase-2 host-framework mix?** If it's predominantly React (Marketplace + a React-rewritten TMS surface), React wins. If it's genuinely mixed (Angular TMS + React Marketplace + vanilla TRC), Lit's framework-agnostic property earns its keep.
2. **Team capability.** Is the team confident shipping Lit, or does the team's React fluency reduce v1 risk materially?
3. **Bundle budget for the Status Card.** Concrete embed sites and their bundle-size constraints. If 5 KB vs 40 KB doesn't bite, React's other advantages win.
4. **The standalone portal's framework choice.** The portal is the v1 surface and will be exercised hardest first. Building it in the team's strongest framework is a real argument.
## Rejected alternatives
- **React micro-frontends without Custom Elements.** Loses the embed-anywhere property; conflicts with Angular TMS surfaces; bundle weight problematic for the `<pv-status-card>` case.
- **Stencil.** Comparable to Lit on the Custom Elements axis; smaller community; fewer codegen-friendly patterns in the training corpus.
- **Vanilla Custom Elements (no library).** Possible, but a thin framework's reactive update model + typed templates pay back the 5–40 KB cost.
- **Dynamic generation in v1.** Promising but unproven; multiplies the contract surface for codegen (every generation produces a new shape that needs accessibility, theming, and event audits). Defer.
## Consequences
- One frontend framework across all five components plus the standalone portal; one bundle pipeline; one test runner (Playwright on real browsers).
- The component prop contracts are TypeScript interfaces, exported as JSON Schemas, regardless of which framework family wins. The schemas are the codegen-pipeline contract.
- If the engineer-review pass flips this ADR to React: the components are written as React components that export Custom Element wrappers (via React 19's `customElements.define(...)` integration). The portal is a React SPA. Phase-2 embedding into Angular TMS surfaces still works through the Custom Element wrapper at a small adapter cost.
- If Lit holds: the portal is a thin Lit-based SPA (or Lit + a lightweight router); React embedding hosts get a thin React adapter wrapper for ergonomic prop passing.
- Either way, **framework-agnostic Custom Elements remain the on-the-wire contract** between Partner Vetting and host applications.

### ADR-013 — Document AI provider: Anthropic Claude with provider abstraction

## Context
Document AI is the engine that turns uploaded carrier documents into typed Result Envelope payloads. The capability requirements:
- **Multilingual** at 25+ languages (LR §«Multilingual Document Processing»). 30+ once North America lands.
- **Mixed document modalities** — scanned PDFs (insurance certificates), structured PDFs (company registrations), photographs of paper documents (carrier-submitted via mobile), spreadsheets, free-text attestations.
- **Structured extraction** to a check-specific typed payload (`{policy_number, insurer, coverage_amount, expiry, geographic_scope, ...}`).
- **Calibrated confidence** per extraction; per-check threshold; sub-threshold routes to human review.
- **Bounded retries** (3 attempts per LR §«Retry and HITL Escalation Contract»).
Providers on the table: Anthropic Claude, OpenAI GPT-class, Azure Document Intelligence, Google Document AI, open-weight model on Azure ML.
## Decision
**Anthropic Claude as the v1 primary provider**, behind a thin **provider abstraction**:
```typescript
interface DocumentAiProvider {
  extract(check_id, check_version, blob_uri): Promise<ResultEnvelope>;
}
```
Provider selection is per-check (not per-call): each Check entry in the catalog names its preferred provider. The abstraction allows per-check provider override and second-model consensus on borderline confidence.
Azure Document Intelligence is reserved as a fallback for high-volume bursts (rate-limit fallback path) and for cases where Anthropic's regional capacity becomes the bottleneck.
## Rejected alternatives
- **OpenAI GPT-class as primary.** Comparable capability; Trimble's broader vendor posture favours Anthropic for Trimble-wide AI work, and the codegen pipeline itself is Anthropic-based — reducing vendor count is a v1 simplification.
- **Azure Document Intelligence as primary.** Strong at structured-PDF OCR; weaker at the natural-language reasoning step (cross-referencing policy number against issuer registry, interpreting a free-text attestation, multilingual handling at the long tail). Better positioned as a fallback for high-volume OCR.
- **Open-weight model self-hosted.** Adds an inference-infrastructure workstream that v1 doesn't have time for. Re-evaluable in Phase 2 if cost or data-residency drives it.
- **Single-provider with no abstraction.** Couples every check definition to one vendor; loses the per-check override option that the catalog model already implies.
## Consequences
- The Document AI Provider Abstraction (§6.2) is one of the most heavily contract-tested boundaries: every provider implementation passes the same eval suite per check. Anthropic Claude is the v1 reference implementation.
- Eval sets per check have ≥ 200 labelled examples covering the language and country mix the check serves. The eval framework rides on Vitest ([ADR-014](#)).
- Calibration: every Result Envelope carries a `confidence ∈ [0,1]`. The Check definition carries `confidence_threshold` (default 0.85). The drift-detection event stream surfaces confidence distribution per check; the self-healing pipeline triggers re-evaluation if a check's confidence shifts beyond a configured envelope.
- The cost: per-call Claude API charges; circuit-breaker + bounded retry budget caps the worst-case multiplier at 3×; rate-limit-bound caching of identical extractions avoids paying twice for the same document.
- The Phase-2 trigger for revisiting: cost-per-vetting becomes the bottleneck, or a tenant demands data residency that Anthropic doesn't satisfy. The abstraction means the swap is a per-check override, not an architecture change.

### ADR-014 — Testing framework family (proposed): backend + frontend coverage with named alternatives

**Status: Proposed — subject to engineer review.** The codegen-first invariants (§9.1) make automated tests the sole quality gate. This ADR commits to the *categories of test* that must exist (unit, integration, property, contract, end-to-end, accessibility, eval-set) and proposes concrete tools for each. Specific tools shift with the language/runtime decision ([ADR-001](https://www.notion.so/36099f3e507f81aaa27cfe2562e72ce8)) and the frontend framework decision ([ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b)).
## Context
Autonomous codegen as the build mechanism (C1) means **no human reviews production-bound code**. The architecture exposes typed contracts at every boundary; the tests are the mechanism that proves the contracts hold.
Coverage must exist on both sides of the stack:
- **Backend** — the service layer, MCP adapter, bounded-context logic, persistence, integration adapters.
- **Frontend** — the five Web Components, the standalone Partner Vetting Portal application, the contracts between components and the internal HTTP boundary.
Both sides need: unit testing, integration testing, property-based testing where state machines exist, contract testing at every typed boundary, and end-to-end testing.
Plus a dedicated **eval-set** mechanism for AI-bearing checks (the Document AI Provider Abstraction, [ADR-013](https://www.notion.so/36099f3e507f812f96bce468019ecbe7)).
## Decision (proposed)
### Coverage gates (invariant — applies regardless of tool choice)
- **≥ 90 % branch coverage** of business logic on both backend and frontend.
- **Property tests on every state-machine transition** (Vetting Run, Submission lifecycle, Grant lifecycle, Result Envelope lifecycle).
- **Contract tests on every typed boundary** (MCP adapter ↔ service; internal HTTP ↔ Web Components; Document AI Provider Abstraction ↔ provider implementations).
- **Eval sets per AI-bearing check** — ≥ 200 labelled examples each, balanced by language and country mix the check serves.
- **Failure-mode (chaos) tests** on every external integration (FMCSA, VAT registries, road haulage permit registries, Anthropic Claude, Trimble ID userinfo, Redis, Key Vault). Nightly.
### Backend stack (proposed, assuming TypeScript/Node.js per [ADR-001](https://www.notion.so/36099f3e507f81aaa27cfe2562e72ce8))
| Test class | Proposed tool | Purpose |
|---|---|---|
| Unit | **Vitest** | Pure-function and module-level tests; fastest feedback loop |
| Integration | **Vitest**  • **testcontainers-node** (ephemeral Postgres + Redis) | Cross-module flows against real persistence; RLS denial-path assertions |
| Property | **fast-check** | State-machine transitions, Result Envelope payload invariants, predicate AST evaluation |
| Contract | **Pact** (consumer-driven) | MCP adapter ↔ service; internal HTTP ↔ Web Components; provider abstractions |
| HTTP integration | **supertest** (or built-in `fetch`-based harness) | Endpoint-level request/response shape against a running service |
| Eval-set (AI) | Vitest-based custom harness; labelled JSONL fixtures per check | Per-check confidence, accuracy, regression detection |
| Load / capacity | Deferred to Phase 2 — **k6** or **Artillery** are the candidates | Throughput envelope, latency under load |
| Chaos / failure-mode | **Toxiproxy**  • Vitest harness | Dependency timeouts, 500s, malformed payloads, identity drift |
### Frontend stack (proposed, assuming Lit or React per [ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b))
| Test class | Proposed tool (Lit) | Proposed tool (React) | Purpose |
|---|---|---|---|
| Component / unit | **Vitest**  • `@open-wc/testing` | **Vitest**  • `@testing-library/react` | Render in isolation; assert behaviour |
| End-to-end (browser) | **Playwright** | **Playwright** | Real-browser flows through the portal; Web Component embedding tests |
| Accessibility | `@axe-core/playwright` | `@axe-core/playwright` | WCAG checks on every component and portal route |
| Visual regression | Playwright snapshots (or **Chromatic** with Storybook) | Playwright snapshots (or **Chromatic** with Storybook) | Catch styling regressions |
| Storybook (optional) | **Storybook**  • Lit add-on | **Storybook**  • React add-on | Component-development isolation; not a test runner but a development-time aid |
### If [ADR-001](https://www.notion.so/36099f3e507f81aaa27cfe2562e72ce8) lands on Go
| Test class | Tool |
|---|---|
| Unit + integration | stdlib `testing`  • `testify` |
| Property | **gopter** or **rapid** |
| Contract | **pact-go** |
| DB integration | stdlib `testing`  • **testcontainers-go** |
| Eval-set | Custom harness on stdlib `testing` |
| Chaos | Toxiproxy + stdlib harness |

The categories don't change; only the tool names do. The codegen contract (test files exist for every contract; coverage gates met) is identical.
## CI pipeline shape (invariant)
The CI pipeline runs in this order regardless of stack:
1. Lint → 2. Type-check → 3. Unit → 4. Property → 5. Contract → 6. Integration (ephemeral Postgres + Redis) → 7. End-to-end (Playwright) → 8. Eval-set (AI checks) → 9. Accessibility.
Targets: ≤ 15 minutes for the fast lane (lint + type-check + unit + property + contract); ≤ 45 minutes for the full lane. A failing eval set blocks the merge.
## Rejected alternatives
- **Jest (backend).** Comparable to Vitest; Vitest's faster execution under Vite and tighter TypeScript ergonomics are the differentiators. Either works; the framework family doesn't depend on this pick.
- **Cypress (frontend E2E).** Comparable to Playwright; Playwright's multi-browser support, native Web Component support, and trace viewer are the differentiators.
- **Mocha + Chai (backend).** No technical reason — Vitest's all-in-one shape is friendlier for codegen.
- **No property tests.** A state machine without property tests is a state machine with hidden transitions. The codegen pipeline can easily produce a happy-path transition that fails on an edge case; property tests catch what happy-path unit tests don't.
- **No contract tests.** The MCP adapter ↔ service boundary is versioned independently in spirit; contract tests are what make that real and survivable across codegen iterations.
## Consequences
- One test runner per stack tier (one for backend, one for frontend); shared harness conventions across both.
- Eval sets are versioned: every check version ships with its labelled set. Drift in production confidence triggers an eval-set re-evaluation specification.
- The CI pipeline's gating discipline is the only thing standing between codegen output and production. Coverage gates + property tests + eval sets are non-negotiable; specific tools can swap.
- The design doc covers concrete test data fixtures, eval-set authoring conventions, the chaos test catalogue, and the load-test budget for the Phase-2 lane.

### ADR-015 — Secret and key management: Azure Key Vault + per-profile Fernet envelope keys

## Context
Three classes of sensitive material need management:
- **Service secrets** — integration credentials (FMCSA API key, VAT registry keys, Anthropic API key, document AI provider tokens), database admin credentials, internal service-to-service tokens.
- **Consent records** — the partner's grant decisions, which are legally sensitive and subject to GDPR erasure.
- **Document blobs** — uploaded carrier documents, subject to the GDPR posture (synthesis Q6) and to the consent/visibility model ([ADR-017](#)).
ARC's posture is the inherited baseline: Fernet AES-128-CBC + HMAC-SHA256 at the application layer before persistence, Azure-managed encryption underneath, TLS in transit, no token values in LLM prompts or traces (ARC-IP «How Arc Agent Secures Tokens»).
The GDPR erasure mechanism is an open question (synthesis Q6): crypto-erasure (per-profile keys destroyed on request, audit metadata retained) or some other mechanism. The architecture has to commit to one because the storage shape depends on it.
## Decision
**Azure Key Vault** as the secret and key custodian (TTC catalog). All service secrets live there; the application reads on cache miss (5-minute TTL).
**Application-layer Fernet AES-128-CBC + HMAC-SHA256** for sensitive payloads at rest (consent records, integration credentials at rest, document blob references). Layered on top of Azure-managed at-rest encryption.
**Per-profile envelope keys** generated on Profile creation; managed in Key Vault; rotated on a 90-day cycle. The envelope key encrypts the profile's document references and consent records. **On GDPR erasure**, the profile's envelope key is destroyed in Key Vault — document blobs and consent records become unreadable; audit metadata is retained.
## Rejected alternatives
- **Field-level encryption with a single tenant key.** Loses the crypto-erasure granularity — one tenant key serves many profiles, so destroying it would erase everyone.
- **Tombstoning + hard delete.** Compatible with audit immutability only by carving exceptions into the audit retention — the legal posture becomes harder to defend than crypto-erasure's "the data is unreadable but the audit metadata is intact."
- **No application-layer encryption (rely on Azure-managed encryption only).** Loses crypto-erasure (Azure's at-rest encryption is per-disk, not per-profile). Loses the defense-in-depth posture against a compromised database operator.
- **HashiCorp Vault.** Comparable on capability; outside the TTC catalog.
## Consequences
- One secret store (Key Vault); rotation policies live there.
- The Consent Manager (§6.1) is the only component that calls Key Vault for envelope-key destruction; the call is audited.
- A `delete_profile` request: destroys the profile's envelope key, emits the GDPR-erasure audit event, retains the audit metadata. Document blobs still exist in Blob but are unreadable. Audit consumers see the deletion event with the metadata intact.
- Key rotation is automated on a 90-day cycle; the rotation re-encrypts the consent records under the new key inside a single transaction; the prior key remains in Key Vault as a soft-deleted version until the audit-retention window passes.
- The cost: per-read overhead for envelope decryption. Hot paths (Status Card render, dashboard queries) operate on metadata only — not the encrypted payloads — so the hot path is not slowed.
- The risk: Key Vault outage takes down the consent layer. Mitigation: Key Vault is one of Azure's higher-SLA services; the circuit-breaker on Key Vault calls falls back to a *read-deny* posture (consent reads fail closed) rather than a stale-cache posture; failure surfaces as an alert immediately.
- Legal review (synthesis C7) confirms the crypto-erasure posture meets the GDPR right-to-erasure. If counsel returns a different verdict, this ADR re-opens.

### ADR-016 — Roles: Platform Admin, Tenant Admin, Tenant User, Partner

## Context
The synthesis flags the role model as OPEN (§6 cross-check `role-architecture-and-federated-identity`, §7 Q1, Q2). The PCD names five user categories plus agent consumers; the wiki proposed four roles; PCD §14 explicitly asks whether the internal Trimble admin should be a hard distinction or expressed through configuration.
The role model has to cover:
- Trimble-internal stewardship of the check catalog and standard rulesets.
- Per-tenant configuration (workflow definition, rule authoring within the catalog, dashboard access, user management within the tenant).
- Per-tenant consumption (viewing vetting status on a host product surface).
- Partners themselves (uploading documents, managing their profile, managing grants).
- The dual-role reality: the same legal entity can be a partner under one tenant's vetting program and a tenant administering its own vetting program against its subcontractors (PCD §5).
## Decision
**Four roles, with Platform Admin on a cross-tenant axis:**
- **Platform Admin** — Trimble-internal. Stewards the Check catalog. Authors standard rulesets (the Trimble-blessed reference shapes that tenants can clone). Can read across tenants for catalog-stewardship purposes; every cross-tenant operation emits `audit_events.cross_tenant=true`. Not the same as "Trimble employee" — only the small set explicitly granted the role.
- **Tenant Admin** — a user inside a tenant who configures rulesets, manages tenant users (role assignments), and views the Vetting Dashboard.
- **Tenant User** — a user inside a tenant who views vetting state on host-product surfaces (Status Card embedding) but does not configure.
- **Partner** — a user authenticated under their partner profile; uploads documents, manages their profile, manages grants. Distinct identity context from Tenant roles.
Role assignment storage: `(user_subject, tenant_id, role)`. No user attributes (name, email, etc.) stored — those resolve from the IdP at request time. The dual-role reality is handled by the fact that the same `user_subject` can carry both a Partner role (under their own partner profile) and a Tenant role (under their tenant) — the per-request middleware selects the active role based on the target endpoint and the token's resolved tenant claim.
## Rejected alternatives
- **Three roles (no Platform Admin axis).** Collapses catalog stewardship into Tenant Admin under a "Trimble tenant"; loses the explicit cross-tenant audit flag and conflates Trimble-internal stewardship with customer-facing tenant operations. PCD §14 specifically asks the question — the answer is to make Platform Admin a separate axis.
- **Five+ roles with a finer split (Platform Admin / Catalog Steward / Tenant Owner / Tenant Admin / Tenant User / Partner).** Premature differentiation. The four-role model accommodates a Phase-2 split (e.g., a Catalog Steward sub-role) without breaking the schema — role names are strings, assignments are rows.
- **No "Partner" as a role; partner identity inferred from claim.** Loses the explicit role and the explicit audit trail. Audit events tagging matters when the partner is a principal in carrier-initiated flows (F30, F35).
- **Role-per-tenant-product (separate Tenant Admin for Marketplace vs TMS).** Conflates product permissions with vetting permissions. Host products do their own permission enforcement; Partner Vetting roles cover Partner Vetting operations.
## Consequences
- The role model is configuration: adding a fifth role in Phase 2 is a schema update + middleware rule update, not a re-architecture.
- Cross-tenant operations are *only* available to Platform Admin; every operation under that escalation emits a distinguishing audit event. The audit consumer can isolate this surface.
- The Partner role's identity context is separate from any Tenant role they may also carry. The dual-role reality (PCD §5 — a carrier vetted by one shipper while administering vetting against their subcontractors) is handled by the per-request middleware selecting the active role based on the target endpoint.
- The MCP tool surface (§8.1) carries role-aware authorisation: `create_ruleset` requires Tenant Admin; `submit_document` requires Partner; `start_vetting_run` is callable by Tenant User, Tenant Admin, or Partner (in carrier-initiated mode).

### ADR-017 — Consent model: per-(tenant, profile) opt-in grants, freeze-on-revoke

## Context
The carrier-owned profile is one of the load-bearing product principles (PCD §7, synthesis F13). Trust Center is the cautionary case — the failure mode was carrier friction and unclear value exchange. Partner Vetting's response is to make the carrier the owner: they upload once, they grant who sees what, they revoke. The mechanics are an open question (synthesis Q4, Q5) with three knobs:
- **Grain** — per-profile, per-section (insurance vs. license vs. company registration), per-document, per-request?
- **Default posture** — opt-in (default off, partner explicitly grants) vs. broader visibility (default on, partner explicitly restricts).
- **Revocation semantics** — freeze (no future visibility, prior Coverage Reports retained by the tenant) vs. hard delete (also retracts prior Coverage Reports) vs. erasure.
Legal review (C7) is a launch gate.
## Decision
- **Grain: per-(tenant, profile, section).** A Grant is one row per `(tenant_id, profile_id, section)`. Sections are coarse (e.g., `core_credentials`, `dangerous_goods`, `north_america_stack`) and aligned with how rulesets group checks — not per-document. Per-document grants are too fine-grained for the UX and too expensive for the audit surface.
- **Default posture: opt-in.** Partners explicitly grant tenant visibility before the tenant can read profile sections. At registration moment when no specific tenant is yet known, the partner sees an optional toggle: "publish core credentials to the Trimble carrier-vetting network" — default off (resolves synthesis Q5).
- **Revocation semantics: freeze.** Revoke ends future visibility. Coverage Reports already delivered to a tenant remain in that tenant's audit trail and dashboard surface — the legal posture is "data was lawfully shared at the time; revocation prevents future sharing." Hard delete is the separate GDPR-erasure path ([ADR-015](#)), distinct from grant revocation.
## Rejected alternatives
- **Per-document grain.** Carrier UX becomes a per-document checkbox dialog at every Vetting Run. Friction-amplifying. Profile-section grain is enough for v1; if Phase 2 surfaces a need for finer grain, the schema accommodates (grant rows are additive).
- **Default visibility broad (opt-out).** Maximises network effect but reproduces the Trust Center failure mode — carriers feel exposed, friction goes up, adoption drops. The carrier-owned principle (PCD §7) demands opt-in.
- **Hard delete on revoke.** Conflicts with audit immutability and with the tenant's legitimate retention of past Coverage Reports under its compliance posture. Hard delete is the GDPR-erasure path, addressed separately.
## Consequences
- The Consent Manager (§6.1) is the only writer of Grant rows. The Profile & Consent context is the only reader on the hot path; other contexts get a typed `is_granted(profile_id, tenant_id, section) → bool` interface.
- Audit trail: every grant issuance and revocation emits an audit event with `(actor, profile_id, tenant_id, section, action ∈ {grant, revoke})`.
- The tenant-facing UI surfaces grant state clearly: "Insurance section: visible to your tenant until 2026-08-01, then re-verification required" — the freshness window flows from the underlying rules.
- The carrier-facing UI shows granted tenants per profile section, with a one-click revoke. Revocation is immediate (RLS denies on the next read); previously-delivered Coverage Reports stay in the tenant's view but are visibly stamped "consent revoked on YYYY-MM-DD; do not rely for future decisions."
- Legal review (C7) confirms the freeze-on-revoke posture and the opt-in default. If counsel returns a different verdict on a specific jurisdiction (Germany's BDSG, for example), the architecture supports per-jurisdiction grant defaults — a configuration knob on Tenant, not a re-architecture.

### ADR-018 — Cross-product propagation: Status Card embedding, no state replication

## Context
Vera today is locked to Marketplace. A carrier vetted in Marketplace is invisible to TMS, visibility, freight procurement, or any other Trimble product. LR §«Cross-Product Identity and Vetting Outcome Propagation» calls this out as the central fragmentation. The new system must eliminate it.
Two propagation models on the table:
- **State replication** — each Trimble product holds a local copy of relevant Partner Vetting state, kept in sync via events (or polling).
- **Embedded reading** — Trimble products embed the Status Card Web Component, which fetches live state from Partner Vetting on render.
The decision also has to address synthesis Q14: when a vetting outcome flows to other products, what label and provenance does it carry? "ARC-vetted", "Vera-vetted", "customer-vetted" are not interchangeable claims.
## Decision
**Embedded reading via the Status Card Web Component. No state replication in v1.**
Every vetting outcome surfaced in any Trimble product is rendered by `<pv-status-card>`, which fetches live state from Partner Vetting's internal HTTP boundary on render. The component shows:
- Per-rule classification (satisfied / missing / stale / version-downgraded / inconclusive), never an aggregate boolean.
- Explicit provenance: `(tenant_id, ruleset_id, ruleset_version, vetted_at, evidence_uri)`. A carrier vetted under Knauf's "Knauf-Standard v3" ruleset is shown as "Vetted by Knauf · Knauf-Standard v3 · 2026-04-12" — never as "verified carrier."
- Per-check evidence link where the consumer's grant allows.
## Rejected alternatives
- **State replication via event bus (Phase 1).** Requires the event bus ([ADR-007](#) defers this) and requires every Trimble product to add a consumer + a local store + a sync discipline. Multiplies the state surfaces; multiplies the chances of drift. Inconsistent state across products is exactly what Vera's split between HCS and Marketplace produced (LR §«Dual Legacy System Fragmentation»); embedded reading is the antidote.
- **State replication via daily batch sync.** Same multiplication, plus the freshness gap (a carrier vetted at 09:00 isn't visible in TMS until tomorrow's batch). Defeats the purpose.
- **State replication via REST poll.** Equivalent to embedded reading in network terms but worse in UX — products need a UI for the state regardless. Embed once via the component.
- **One aggregate "verified" boolean.** Forbidden by C10. Loses provenance, loses tenant attribution, loses the per-rule basis for the signal.
## Consequences
- Partner Vetting is the single source of truth for vetting state. Other products read; they don't replicate.
- The Status Card render path becomes a hot path; it's on the read-mostly side of the load profile and benefits from the IdP attribute and integration response caches.
- Tenant attribution is explicit in every render. "Verified carrier" doesn't exist as a label anywhere in the system.
- The Phase-2 trigger for revisiting: a Trimble product team surfaces a concrete need for state replication (e.g., offline-capable mobile dispatch needing pre-fetched vetting state). The architecture accommodates: Partner Vetting publishes outbox events that a product-side consumer can subscribe to via Service Bus (if and when Service Bus lands per [ADR-007](#)).
- The risk: a Partner Vetting outage takes down the Status Card surface in every host product. Mitigation: the component renders a graceful "vetting service temporarily unavailable" state with the last-known cache value where available; host products are not held hostage by Partner Vetting's availability on critical-path operations (e.g., a Marketplace bid can still close — the bid's *recorded* vetting state is what was checked at bid time, not what the Status Card shows right now).

### ADR-019 — v1 UI delivery: standalone Partner Vetting Portal alongside embeddable Web Components

## Context
v1 needs a user-facing surface for two distinct audiences:
- **Partners** — upload documents, manage profile, manage tenant grants, see their full vetting history across all shippers.
- **Tenant operators (Tenant Admin + Tenant User)** — configure rulesets, view dashboards, see per-partner Coverage Reports.
- **Platform Admins** — steward the check catalog and standard rulesets, run cross-tenant operations.
The architecture commits to a family of five Web Components ([ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b)) — Status Card, Workflow Configuration, Vetting Dashboard, Partner Submission, Partner Profile — intended to be embeddable in many host products. Two viable v1 hosting strategies:
1. **Embedded-only:** ship the components and let host products (Marketplace, TMS family, Transporeon Registration Center) embed them. Partner Vetting v1 launch is gated by those host teams' integration timelines.
2. **Standalone portal first:** ship a TTC-hosted single-page app that mounts the same components under one login, then bring embedding online in Phase 2.
Knauf is the v1 customer. Marketplace, TMS, and TRC integrations are Phase-2 work — none of those host teams are committed to ship Partner Vetting embeds inside the v1 window. The team is six non-engineers ([ADR-008](https://www.notion.so/36099f3e507f8181ba18fc11b03151e1)) building via autonomous codegen, with a two-month v1 deadline.
## Decision
**v1 ships a standalone Partner Vetting Portal.** A TTC-hosted single-page app behind Trimble ID OIDC login that mounts all five Web Components (Status Card, Workflow Configuration, Vetting Dashboard, Partner Submission, Partner Profile) with role-driven routing. Same components, single host.
Phase-2 brings embedding online in Marketplace, TMS family, Transporeon Registration Center, and (Phase 3) a Trimble-built host for external customers without a Transporeon relationship.
## Why
- **One controlled surface for v1 validation.** Engineers, design, Knauf, and product all exercise the full UI in one place before any embedding lands in another product. The portal *is* the validation venue.
- **Decouples v1 release from other product teams' timelines.** Partner Vetting v1 ships when its own code is ready, not when Marketplace or TMS finish their embedding integration.
- **Marginal cost.** The portal is layout + auth + routing around components that are already being built for embedding. No additional component work; one extra surface to maintain.
- **Knauf compliance teams need a deterministic non-agent surface.** ARC/Mario via MCP is one of the two v1 caller surfaces, but compliance work and ruleset configuration land more naturally in a deterministic UI than in a chat agent.
- **Partners need a home that isn't tied to one host product.** The Partner Profile component renders the partner's complete vetting record across every tenant they've worked with — a view that doesn't fit naturally inside any one Trimble product's UI. The portal is the natural home for it.
- **Phase-2 embedding becomes mechanical.** Once components are exercised in the portal, embedding into Marketplace and TMS reduces to a `<script type="module">` + custom-element-tag integration with the working portal as the visual reference.
## Rejected alternatives
- **Embedded-only in v1.** Requires every host product to ship integration work before Partner Vetting can be used by anyone. Couples Partner Vetting's v1 release to Marketplace and TMS team timelines, and adds Transporeon Registration Center as a third dependency for the carrier-facing flow. Not viable for the two-month v1 deadline.
- **Both standalone portal AND broad embedding in v1.** Scope creep. Pulls Phase-2 work forward without payoff and multiplies integration risk during the v1 window.
- **Separate UI implementations for portal vs. embedded.** Doubles the UI surface; loses the "build once, host anywhere" property the Web Component family is designed for. Defeats the v1-as-validation-venue argument.
- **MCP-only in v1, no UI at all.** Considered. Knauf compliance teams need a non-agent surface for steady-state work; partners need somewhere to see and manage their profile; and a Mario-only v1 raises the customer-acceptance bar unnecessarily.
## Consequences
- **The portal is the v1 user-facing surface for all roles.** Platform Admin manages the check catalog and runs cross-tenant operations; Tenant Admin configures rulesets and manages tenant users; Tenant User views dashboards and per-partner Coverage Reports; Partner uploads documents (Partner Submission), and sees the full picture of their profile, document history, vettings, and shipper connections (Partner Profile).
- **The carrier-facing flow lives in the portal in v1.** Synthesis Q19 was previously resolved to "Transporeon Registration Center in v1." This ADR overrides that — TRC integration becomes Phase 2 alongside Marketplace and TMS embedding.
- **Phase 2 onboarding is a pure embedding exercise.** Trimble products as tenants ingest the same components the portal proves out. The team doing the embedding consumes the Web Component catalog (§9.6) and references the portal as the working integration target.
- **Auth handoff is straightforward.** The portal authenticates the user with Trimble ID OIDC, then the components fetch from the internal HTTP boundary with the user's session token. Same auth model as Phase-2 embedding, just hosted by Partner Vetting rather than by a third-party product.
- **The portal lives under the same Azure Static Web Apps host** as the Web Component delivery layer (§5, §10). One CDN, one deploy pipeline, one set of TTC resources.
- **Framework choice is shared with the component family** ([ADR-012](https://www.notion.so/36099f3e507f812789a0e26b23cca41b)). If the engineer-review pass picks React for components, the portal is a React SPA. If Lit holds, the portal is a Lit-based SPA. Either way, no separate frontend stack.
- **v3+ external-customer standalone host** still exists as Phase-3 work — it is not the same artefact as the v1 portal. The v1 portal authenticates against Trimble ID only; the v3+ host adds external customer IdP federation, public-facing pricing/onboarding flows, and a different deployment posture.

---

As a senior architect, critically evaluate this architectural proposal
through the lens of its stated primary constraint: every line of
implementation will be produced by an autonomous AI codegen pipeline —
no human PR review, no human code inspection. Automated tests are the
only quality gate.

Where does this architecture enable that constraint? Where does it
undermine it? What needs to change?

Generate SVG diagrams if a visual would make a key finding materially
clearer.

---
