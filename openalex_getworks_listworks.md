> ## Documentation Index
> Fetch the complete documentation index at: https://developers.openalex.org/llms.txt
> Use this file to discover all available pages before exploring further.

# Get a single work

> Retrieve a single work by its OpenAlex ID or external ID (DOI, PMID, PMCID, MAG ID). External IDs can be passed as full URLs or URN format (e.g., `doi:10.1234/example` or `pmid:12345678`).



## OpenAPI

````yaml /api-reference/openapi.json get /works/{id}
openapi: 3.1.0
info:
  title: OpenAlex API
  description: >-
    The OpenAlex API provides access to a comprehensive catalog of scholarly
    works, authors, sources, institutions, topics, keywords, publishers, and
    funders. OpenAlex indexes over 250 million scholarly works.
  version: 1.0.0
  contact:
    name: OpenAlex Support
    email: support@openalex.org
    url: https://openalex.org
  license:
    name: CC0
    url: https://creativecommons.org/publicdomain/zero/1.0/
servers:
  - url: https://api.openalex.org
    description: OpenAlex Production API
security:
  - apiKey: []
tags:
  - name: Works
    description: Scholarly documents like journal articles, books, datasets, and theses
  - name: Authors
    description: People who create scholarly works
  - name: Sources
    description: Journals, repositories, and other venues where works are hosted
  - name: Institutions
    description: Universities, research organizations, and other affiliations
  - name: Topics
    description: Research topics automatically assigned to works
  - name: Keywords
    description: Short phrases identified from works' topics
  - name: Publishers
    description: Companies and organizations that publish scholarly works
  - name: Funders
    description: Organizations that fund research
  - name: Autocomplete
    description: Fast typeahead search for any entity type
  - name: Domains
    description: Top-level categories in the topic hierarchy (4 total)
  - name: Fields
    description: Second-level categories in the topic hierarchy (26 total)
  - name: Subfields
    description: Third-level categories in the topic hierarchy (254 total)
  - name: SDGs
    description: UN Sustainable Development Goals (17 total)
  - name: Countries
    description: Geographic countries for filtering research by location
  - name: Continents
    description: Geographic continents (7 total)
  - name: Languages
    description: Languages of scholarly works
  - name: Awards
    description: Research grants and funding awards
  - name: Concepts
    description: Legacy taxonomy of research areas (deprecated - use Topics instead)
  - name: Work Types
    description: Types of scholarly works (article, book, dataset, etc.)
  - name: Source Types
    description: Types of sources (journal, repository, conference, etc.)
  - name: Institution Types
    description: Types of institutions (education, healthcare, company, etc.)
  - name: Licenses
    description: Open access licenses (CC BY, CC BY-SA, etc.)
paths:
  /works/{id}:
    get:
      tags:
        - Works
      summary: Get a single work
      description: >-
        Retrieve a single work by its OpenAlex ID or external ID (DOI, PMID,
        PMCID, MAG ID). External IDs can be passed as full URLs or URN format
        (e.g., `doi:10.1234/example` or `pmid:12345678`).
      operationId: getWork
      parameters:
        - name: id
          in: path
          required: true
          description: >-
            OpenAlex ID (e.g., W2741809807) or external ID (DOI, PMID, PMCID,
            MAG)
          schema:
            type: string
          examples:
            openalex:
              value: W2741809807
              summary: OpenAlex ID
            doi:
              value: https://doi.org/10.7717/peerj.4375
              summary: DOI URL
            pmid:
              value: pmid:29456894
              summary: PubMed ID (URN format)
        - $ref: '#/components/parameters/select'
        - $ref: '#/components/parameters/api_key'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Work'
        '404':
          $ref: '#/components/responses/NotFound'
        '429':
          $ref: '#/components/responses/RateLimited'
components:
  parameters:
    select:
      name: select
      in: query
      description: >-
        Comma-separated list of fields to return. Reduces response size.
        Example: `select=id,display_name,cited_by_count`
      schema:
        type: string
    api_key:
      name: api_key
      in: query
      description: >-
        Your OpenAlex API key (required). Get a free key at
        https://openalex.org/settings/api
      required: true
      schema:
        type: string
  schemas:
    Work:
      type: object
      description: A scholarly document (article, book, dataset, thesis, etc.)
      properties:
        id:
          type: string
          description: The OpenAlex ID for this work.
          example: https://openalex.org/W2741809807
        doi:
          type: string
          nullable: true
          description: The DOI for the work. This is the Canonical External ID for works.
          example: https://doi.org/10.7717/peerj.4375
        title:
          type: string
          nullable: true
          description: The title of this work.
        display_name:
          type: string
          description: Same as `title`. Included for consistency with other entities.
        publication_year:
          type: integer
          nullable: true
          description: The year this work was published.
        publication_date:
          type: string
          format: date
          nullable: true
          description: The day when this work was published (ISO 8601 format).
        type:
          type: string
          description: >-
            The type of the work. Common values: `article`, `book`, `dataset`,
            `preprint`, `dissertation`, `book-chapter`.
        language:
          type: string
          nullable: true
          description: '[Language](/api-reference/languages) in ISO 639-1 format'
        cited_by_count:
          type: integer
          description: The number of citations to this work.
        is_retracted:
          type: boolean
          description: >-
            True if this work has been retracted (from Retraction Watch
            database).
        is_paratext:
          type: boolean
          description: >-
            True if this work is paratext (e.g., front cover, table of
            contents).
        primary_location:
          $ref: '#/components/schemas/Location'
          description: >-
            A Location object with the primary location of this work (closest to
            the version of record). Includes `source`, `landing_page_url`,
            `pdf_url`, `is_oa`, `license`, and `version`.
        locations:
          type: array
          items:
            $ref: '#/components/schemas/Location'
          description: >-
            List of Location objects describing all unique places where this
            work lives.
        best_oa_location:
          $ref: '#/components/schemas/Location'
          description: >-
            A Location object with the best available open access location for
            this work.
        open_access:
          $ref: '#/components/schemas/OpenAccess'
          description: 'Information about the access status of this work:'
        authorships:
          type: array
          items:
            $ref: '#/components/schemas/Authorship'
          description: >-
            List of Authorship objects representing authors and their
            institutions. Limited to the first 100 authors. Each authorship
            includes `author`, `institutions`, `author_position`,
            `is_corresponding`, and other fields.
        ids:
          type: object
          description: 'External identifiers: `openalex`, `doi`, `mag`, `pmid`, `pmcid`.'
          properties:
            openalex:
              type: string
            doi:
              type: string
            mag:
              type: integer
            pmid:
              type: string
            pmcid:
              type: string
        biblio:
          type: object
          description: 'Bibliographic info: `volume`, `issue`, `first_page`, `last_page`.'
          properties:
            volume:
              type: string
              nullable: true
            issue:
              type: string
              nullable: true
            first_page:
              type: string
              nullable: true
            last_page:
              type: string
              nullable: true
        abstract_inverted_index:
          type: object
          nullable: true
          description: >-
            The abstract as an inverted index (word positions). OpenAlex doesn't
            include plaintext abstracts due to legal constraints. Use the
            `has_abstract` filter to get works with or without abstracts.
        referenced_works:
          type: array
          items:
            type: string
          description: OpenAlex IDs for works that this work cites.
        referenced_works_count:
          type: integer
          description: The number of works that this work cites.
        related_works:
          type: array
          items:
            type: string
          description: >-
            OpenAlex IDs for works related to this work (computed
            algorithmically).
        topics:
          type: array
          items:
            $ref: '#/components/schemas/WorkTopic'
          description: List of up to 3 Topics for this work, each with a relevance score.
        primary_topic:
          $ref: '#/components/schemas/WorkTopic'
          description: >-
            The top ranked Topic for this work, with `id`, `display_name`,
            `score`, and hierarchy (`subfield`, `field`, `domain`).
        keywords:
          type: array
          items:
            $ref: '#/components/schemas/WorkKeyword'
          description: >-
            Keywords identified based on the work's topics, with relevance
            scores.
        funders:
          type: array
          items:
            $ref: '#/components/schemas/DehydratedFunder'
          description: Dehydrated Funder objects representing the funders of this work.
        awards:
          type: array
          items:
            $ref: '#/components/schemas/Award'
          description: >-
            Dehydrated Award objects representing grants associated with this
            work.
        fwci:
          type: number
          nullable: true
          description: >-
            Field-weighted Citation Impact, calculated as citations received /
            citations expected.
        citation_normalized_percentile:
          type: object
          nullable: true
          properties:
            value:
              type: number
            is_in_top_1_percent:
              type: boolean
            is_in_top_10_percent:
              type: boolean
          description: >-
            Percentile of citation count normalized by work type, year, and
            subfield. Includes `value`, `is_in_top_1_percent`,
            `is_in_top_10_percent`.
        cited_by_percentile_year:
          type: object
          nullable: true
          properties:
            min:
              type: integer
            max:
              type: integer
          description: >-
            Percentile rank compared to other works published in the same year.
            Contains `min` and `max`.
        counts_by_year:
          type: array
          items:
            type: object
            properties:
              year:
                type: integer
              cited_by_count:
                type: integer
          description: '`cited_by_count` for each of the last ten years.'
        sustainable_development_goals:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              display_name:
                type: string
              score:
                type: number
          description: >-
            UN Sustainable Development Goals relevant to this work, with
            prediction scores.
        mesh:
          type: array
          items:
            type: object
            properties:
              descriptor_ui:
                type: string
              descriptor_name:
                type: string
              qualifier_ui:
                type: string
              qualifier_name:
                type: string
              is_major_topic:
                type: boolean
          description: MeSH tags for works found in PubMed.
        indexed_in:
          type: array
          items:
            type: string
          description: >-
            Sources this work is indexed in. Values: `arxiv`, `crossref`,
            `doaj`, `pubmed`.
        has_content:
          type: object
          nullable: true
          properties:
            pdf:
              type: boolean
            grobid_xml:
              type: boolean
          description: 'Information about downloadable full-text content:'
        content_url:
          type: string
          nullable: true
          description: >-
            URL for downloading full-text content. Only present when
            `has_content.pdf` or `has_content.grobid_xml` is true.
        created_date:
          type: string
          format: date
          description: When this work was added to OpenAlex (ISO 8601 date).
        updated_date:
          type: string
          format: date-time
          description: When this work was last updated (ISO 8601 datetime).
    Location:
      type: object
      description: Where a work is hosted
      properties:
        is_oa:
          type: boolean
          description: Whether this location provides open access
        landing_page_url:
          type: string
          nullable: true
          description: URL to the landing page
        pdf_url:
          type: string
          nullable: true
          description: Direct URL to PDF
        source:
          $ref: '#/components/schemas/DehydratedSource'
          description: >-
            [Dehydrated
            source](/api-reference/sources#the-dehydratedsource-object)
        license:
          type: string
          nullable: true
          description: The [license](/api-reference/licenses) (e.g., cc-by)
        license_id:
          type: string
          nullable: true
        version:
          type: string
          nullable: true
          enum:
            - publishedVersion
            - acceptedVersion
            - submittedVersion
          description: Version of the work at this location
        is_accepted:
          type: boolean
        is_published:
          type: boolean
    OpenAccess:
      type: object
      description: Open access information
      properties:
        is_oa:
          type: boolean
          description: Whether this work is open access
        oa_status:
          type: string
          enum:
            - diamond
            - gold
            - hybrid
            - bronze
            - green
            - closed
          description: Open access status
        oa_url:
          type: string
          nullable: true
          description: Best open access URL
        any_repository_has_fulltext:
          type: boolean
          description: Whether any repository has the full text
    Authorship:
      type: object
      description: Author and their affiliation for a work
      properties:
        author_position:
          type: string
          enum:
            - first
            - middle
            - last
          description: Position in author list
        author:
          $ref: '#/components/schemas/DehydratedAuthor'
          description: >-
            [Dehydrated
            author](/api-reference/authors#the-dehydratedauthor-object)
        institutions:
          type: array
          items:
            $ref: '#/components/schemas/DehydratedInstitution'
          description: >-
            [Dehydrated
            institutions](/api-reference/institutions#the-dehydratedinstitution-object)
        countries:
          type: array
          items:
            type: string
          description: Country codes of affiliations
        is_corresponding:
          type: boolean
          description: Whether this is the corresponding author
        raw_author_name:
          type: string
          description: Author name as it appears in the work
        raw_affiliation_strings:
          type: array
          items:
            type: string
    WorkTopic:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        score:
          type: number
        subfield:
          type: object
          properties:
            id:
              type: string
            display_name:
              type: string
          description: The parent [subfield](/api-reference/subfields)
        field:
          type: object
          properties:
            id:
              type: string
            display_name:
              type: string
          description: The parent [field](/api-reference/fields)
        domain:
          type: object
          properties:
            id:
              type: string
            display_name:
              type: string
          description: The parent [domain](/api-reference/domains)
    WorkKeyword:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        score:
          type: number
    DehydratedFunder:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        ror:
          type: string
          nullable: true
      description: >-
        [Dehydrated Funder](/api-reference/funders) — reduced-field version used
        in nested contexts
    Award:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        funder_award_id:
          type: string
        funder_id:
          type: string
        funder_display_name:
          type: string
        doi:
          type: string
          nullable: true
    Error:
      type: object
      properties:
        error:
          type: string
          description: Error type
        message:
          type: string
          description: Human-readable error message
    DehydratedSource:
      type: object
      description: >-
        [Dehydrated Source](/api-reference/sources#the-dehydratedsource-object)
        — reduced-field version used in nested contexts
      properties:
        id:
          type: string
        display_name:
          type: string
        issn_l:
          type: string
          nullable: true
        issn:
          type: array
          items:
            type: string
          nullable: true
        is_oa:
          type: boolean
        is_in_doaj:
          type: boolean
        is_core:
          type: boolean
        host_organization:
          type: string
          nullable: true
        host_organization_name:
          type: string
          nullable: true
        host_organization_lineage:
          type: array
          items:
            type: string
        type:
          type: string
          description: The [source type](/api-reference/source-types)
    DehydratedAuthor:
      type: object
      description: >-
        [Dehydrated Author](/api-reference/authors#the-dehydratedauthor-object)
        — reduced-field version used in nested contexts
      properties:
        id:
          type: string
        display_name:
          type: string
        orcid:
          type: string
          nullable: true
    DehydratedInstitution:
      type: object
      description: >-
        [Dehydrated
        Institution](/api-reference/institutions#the-dehydratedinstitution-object)
        — reduced-field version used in nested contexts
      properties:
        id:
          type: string
        display_name:
          type: string
        ror:
          type: string
          nullable: true
        country_code:
          type: string
          nullable: true
          description: '[Country](/api-reference/countries) code'
        type:
          type: string
          description: The [institution type](/api-reference/institution-types)
        lineage:
          type: array
          items:
            type: string
  responses:
    NotFound:
      description: Entity not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    RateLimited:
      description: Rate limit exceeded
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
  securitySchemes:
    apiKey:
      type: apiKey
      in: query
      name: api_key
      description: >-
        Your OpenAlex API key. Get a free key at
        https://openalex.org/settings/api

````

Built with [Mintlify](https://mintlify.com).

> ## Documentation Index
> Fetch the complete documentation index at: https://developers.openalex.org/llms.txt
> Use this file to discover all available pages before exploring further.

# Get a single work

> Retrieve a single work by its OpenAlex ID or external ID (DOI, PMID, PMCID, MAG ID). External IDs can be passed as full URLs or URN format (e.g., `doi:10.1234/example` or `pmid:12345678`).



## OpenAPI

````yaml /api-reference/openapi.json get /works/{id}
openapi: 3.1.0
info:
  title: OpenAlex API
  description: >-
    The OpenAlex API provides access to a comprehensive catalog of scholarly
    works, authors, sources, institutions, topics, keywords, publishers, and
    funders. OpenAlex indexes over 250 million scholarly works.
  version: 1.0.0
  contact:
    name: OpenAlex Support
    email: support@openalex.org
    url: https://openalex.org
  license:
    name: CC0
    url: https://creativecommons.org/publicdomain/zero/1.0/
servers:
  - url: https://api.openalex.org
    description: OpenAlex Production API
security:
  - apiKey: []
tags:
  - name: Works
    description: Scholarly documents like journal articles, books, datasets, and theses
  - name: Authors
    description: People who create scholarly works
  - name: Sources
    description: Journals, repositories, and other venues where works are hosted
  - name: Institutions
    description: Universities, research organizations, and other affiliations
  - name: Topics
    description: Research topics automatically assigned to works
  - name: Keywords
    description: Short phrases identified from works' topics
  - name: Publishers
    description: Companies and organizations that publish scholarly works
  - name: Funders
    description: Organizations that fund research
  - name: Autocomplete
    description: Fast typeahead search for any entity type
  - name: Domains
    description: Top-level categories in the topic hierarchy (4 total)
  - name: Fields
    description: Second-level categories in the topic hierarchy (26 total)
  - name: Subfields
    description: Third-level categories in the topic hierarchy (254 total)
  - name: SDGs
    description: UN Sustainable Development Goals (17 total)
  - name: Countries
    description: Geographic countries for filtering research by location
  - name: Continents
    description: Geographic continents (7 total)
  - name: Languages
    description: Languages of scholarly works
  - name: Awards
    description: Research grants and funding awards
  - name: Concepts
    description: Legacy taxonomy of research areas (deprecated - use Topics instead)
  - name: Work Types
    description: Types of scholarly works (article, book, dataset, etc.)
  - name: Source Types
    description: Types of sources (journal, repository, conference, etc.)
  - name: Institution Types
    description: Types of institutions (education, healthcare, company, etc.)
  - name: Licenses
    description: Open access licenses (CC BY, CC BY-SA, etc.)
paths:
  /works/{id}:
    get:
      tags:
        - Works
      summary: Get a single work
      description: >-
        Retrieve a single work by its OpenAlex ID or external ID (DOI, PMID,
        PMCID, MAG ID). External IDs can be passed as full URLs or URN format
        (e.g., `doi:10.1234/example` or `pmid:12345678`).
      operationId: getWork
      parameters:
        - name: id
          in: path
          required: true
          description: >-
            OpenAlex ID (e.g., W2741809807) or external ID (DOI, PMID, PMCID,
            MAG)
          schema:
            type: string
          examples:
            openalex:
              value: W2741809807
              summary: OpenAlex ID
            doi:
              value: https://doi.org/10.7717/peerj.4375
              summary: DOI URL
            pmid:
              value: pmid:29456894
              summary: PubMed ID (URN format)
        - $ref: '#/components/parameters/select'
        - $ref: '#/components/parameters/api_key'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Work'
        '404':
          $ref: '#/components/responses/NotFound'
        '429':
          $ref: '#/components/responses/RateLimited'
components:
  parameters:
    select:
      name: select
      in: query
      description: >-
        Comma-separated list of fields to return. Reduces response size.
        Example: `select=id,display_name,cited_by_count`
      schema:
        type: string
    api_key:
      name: api_key
      in: query
      description: >-
        Your OpenAlex API key (required). Get a free key at
        https://openalex.org/settings/api
      required: true
      schema:
        type: string
  schemas:
    Work:
      type: object
      description: A scholarly document (article, book, dataset, thesis, etc.)
      properties:
        id:
          type: string
          description: The OpenAlex ID for this work.
          example: https://openalex.org/W2741809807
        doi:
          type: string
          nullable: true
          description: The DOI for the work. This is the Canonical External ID for works.
          example: https://doi.org/10.7717/peerj.4375
        title:
          type: string
          nullable: true
          description: The title of this work.
        display_name:
          type: string
          description: Same as `title`. Included for consistency with other entities.
        publication_year:
          type: integer
          nullable: true
          description: The year this work was published.
        publication_date:
          type: string
          format: date
          nullable: true
          description: The day when this work was published (ISO 8601 format).
        type:
          type: string
          description: >-
            The type of the work. Common values: `article`, `book`, `dataset`,
            `preprint`, `dissertation`, `book-chapter`.
        language:
          type: string
          nullable: true
          description: '[Language](/api-reference/languages) in ISO 639-1 format'
        cited_by_count:
          type: integer
          description: The number of citations to this work.
        is_retracted:
          type: boolean
          description: >-
            True if this work has been retracted (from Retraction Watch
            database).
        is_paratext:
          type: boolean
          description: >-
            True if this work is paratext (e.g., front cover, table of
            contents).
        primary_location:
          $ref: '#/components/schemas/Location'
          description: >-
            A Location object with the primary location of this work (closest to
            the version of record). Includes `source`, `landing_page_url`,
            `pdf_url`, `is_oa`, `license`, and `version`.
        locations:
          type: array
          items:
            $ref: '#/components/schemas/Location'
          description: >-
            List of Location objects describing all unique places where this
            work lives.
        best_oa_location:
          $ref: '#/components/schemas/Location'
          description: >-
            A Location object with the best available open access location for
            this work.
        open_access:
          $ref: '#/components/schemas/OpenAccess'
          description: 'Information about the access status of this work:'
        authorships:
          type: array
          items:
            $ref: '#/components/schemas/Authorship'
          description: >-
            List of Authorship objects representing authors and their
            institutions. Limited to the first 100 authors. Each authorship
            includes `author`, `institutions`, `author_position`,
            `is_corresponding`, and other fields.
        ids:
          type: object
          description: 'External identifiers: `openalex`, `doi`, `mag`, `pmid`, `pmcid`.'
          properties:
            openalex:
              type: string
            doi:
              type: string
            mag:
              type: integer
            pmid:
              type: string
            pmcid:
              type: string
        biblio:
          type: object
          description: 'Bibliographic info: `volume`, `issue`, `first_page`, `last_page`.'
          properties:
            volume:
              type: string
              nullable: true
            issue:
              type: string
              nullable: true
            first_page:
              type: string
              nullable: true
            last_page:
              type: string
              nullable: true
        abstract_inverted_index:
          type: object
          nullable: true
          description: >-
            The abstract as an inverted index (word positions). OpenAlex doesn't
            include plaintext abstracts due to legal constraints. Use the
            `has_abstract` filter to get works with or without abstracts.
        referenced_works:
          type: array
          items:
            type: string
          description: OpenAlex IDs for works that this work cites.
        referenced_works_count:
          type: integer
          description: The number of works that this work cites.
        related_works:
          type: array
          items:
            type: string
          description: >-
            OpenAlex IDs for works related to this work (computed
            algorithmically).
        topics:
          type: array
          items:
            $ref: '#/components/schemas/WorkTopic'
          description: List of up to 3 Topics for this work, each with a relevance score.
        primary_topic:
          $ref: '#/components/schemas/WorkTopic'
          description: >-
            The top ranked Topic for this work, with `id`, `display_name`,
            `score`, and hierarchy (`subfield`, `field`, `domain`).
        keywords:
          type: array
          items:
            $ref: '#/components/schemas/WorkKeyword'
          description: >-
            Keywords identified based on the work's topics, with relevance
            scores.
        funders:
          type: array
          items:
            $ref: '#/components/schemas/DehydratedFunder'
          description: Dehydrated Funder objects representing the funders of this work.
        awards:
          type: array
          items:
            $ref: '#/components/schemas/Award'
          description: >-
            Dehydrated Award objects representing grants associated with this
            work.
        fwci:
          type: number
          nullable: true
          description: >-
            Field-weighted Citation Impact, calculated as citations received /
            citations expected.
        citation_normalized_percentile:
          type: object
          nullable: true
          properties:
            value:
              type: number
            is_in_top_1_percent:
              type: boolean
            is_in_top_10_percent:
              type: boolean
          description: >-
            Percentile of citation count normalized by work type, year, and
            subfield. Includes `value`, `is_in_top_1_percent`,
            `is_in_top_10_percent`.
        cited_by_percentile_year:
          type: object
          nullable: true
          properties:
            min:
              type: integer
            max:
              type: integer
          description: >-
            Percentile rank compared to other works published in the same year.
            Contains `min` and `max`.
        counts_by_year:
          type: array
          items:
            type: object
            properties:
              year:
                type: integer
              cited_by_count:
                type: integer
          description: '`cited_by_count` for each of the last ten years.'
        sustainable_development_goals:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              display_name:
                type: string
              score:
                type: number
          description: >-
            UN Sustainable Development Goals relevant to this work, with
            prediction scores.
        mesh:
          type: array
          items:
            type: object
            properties:
              descriptor_ui:
                type: string
              descriptor_name:
                type: string
              qualifier_ui:
                type: string
              qualifier_name:
                type: string
              is_major_topic:
                type: boolean
          description: MeSH tags for works found in PubMed.
        indexed_in:
          type: array
          items:
            type: string
          description: >-
            Sources this work is indexed in. Values: `arxiv`, `crossref`,
            `doaj`, `pubmed`.
        has_content:
          type: object
          nullable: true
          properties:
            pdf:
              type: boolean
            grobid_xml:
              type: boolean
          description: 'Information about downloadable full-text content:'
        content_url:
          type: string
          nullable: true
          description: >-
            URL for downloading full-text content. Only present when
            `has_content.pdf` or `has_content.grobid_xml` is true.
        created_date:
          type: string
          format: date
          description: When this work was added to OpenAlex (ISO 8601 date).
        updated_date:
          type: string
          format: date-time
          description: When this work was last updated (ISO 8601 datetime).
    Location:
      type: object
      description: Where a work is hosted
      properties:
        is_oa:
          type: boolean
          description: Whether this location provides open access
        landing_page_url:
          type: string
          nullable: true
          description: URL to the landing page
        pdf_url:
          type: string
          nullable: true
          description: Direct URL to PDF
        source:
          $ref: '#/components/schemas/DehydratedSource'
          description: >-
            [Dehydrated
            source](/api-reference/sources#the-dehydratedsource-object)
        license:
          type: string
          nullable: true
          description: The [license](/api-reference/licenses) (e.g., cc-by)
        license_id:
          type: string
          nullable: true
        version:
          type: string
          nullable: true
          enum:
            - publishedVersion
            - acceptedVersion
            - submittedVersion
          description: Version of the work at this location
        is_accepted:
          type: boolean
        is_published:
          type: boolean
    OpenAccess:
      type: object
      description: Open access information
      properties:
        is_oa:
          type: boolean
          description: Whether this work is open access
        oa_status:
          type: string
          enum:
            - diamond
            - gold
            - hybrid
            - bronze
            - green
            - closed
          description: Open access status
        oa_url:
          type: string
          nullable: true
          description: Best open access URL
        any_repository_has_fulltext:
          type: boolean
          description: Whether any repository has the full text
    Authorship:
      type: object
      description: Author and their affiliation for a work
      properties:
        author_position:
          type: string
          enum:
            - first
            - middle
            - last
          description: Position in author list
        author:
          $ref: '#/components/schemas/DehydratedAuthor'
          description: >-
            [Dehydrated
            author](/api-reference/authors#the-dehydratedauthor-object)
        institutions:
          type: array
          items:
            $ref: '#/components/schemas/DehydratedInstitution'
          description: >-
            [Dehydrated
            institutions](/api-reference/institutions#the-dehydratedinstitution-object)
        countries:
          type: array
          items:
            type: string
          description: Country codes of affiliations
        is_corresponding:
          type: boolean
          description: Whether this is the corresponding author
        raw_author_name:
          type: string
          description: Author name as it appears in the work
        raw_affiliation_strings:
          type: array
          items:
            type: string
    WorkTopic:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        score:
          type: number
        subfield:
          type: object
          properties:
            id:
              type: string
            display_name:
              type: string
          description: The parent [subfield](/api-reference/subfields)
        field:
          type: object
          properties:
            id:
              type: string
            display_name:
              type: string
          description: The parent [field](/api-reference/fields)
        domain:
          type: object
          properties:
            id:
              type: string
            display_name:
              type: string
          description: The parent [domain](/api-reference/domains)
    WorkKeyword:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        score:
          type: number
    DehydratedFunder:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        ror:
          type: string
          nullable: true
      description: >-
        [Dehydrated Funder](/api-reference/funders) — reduced-field version used
        in nested contexts
    Award:
      type: object
      properties:
        id:
          type: string
        display_name:
          type: string
        funder_award_id:
          type: string
        funder_id:
          type: string
        funder_display_name:
          type: string
        doi:
          type: string
          nullable: true
    Error:
      type: object
      properties:
        error:
          type: string
          description: Error type
        message:
          type: string
          description: Human-readable error message
    DehydratedSource:
      type: object
      description: >-
        [Dehydrated Source](/api-reference/sources#the-dehydratedsource-object)
        — reduced-field version used in nested contexts
      properties:
        id:
          type: string
        display_name:
          type: string
        issn_l:
          type: string
          nullable: true
        issn:
          type: array
          items:
            type: string
          nullable: true
        is_oa:
          type: boolean
        is_in_doaj:
          type: boolean
        is_core:
          type: boolean
        host_organization:
          type: string
          nullable: true
        host_organization_name:
          type: string
          nullable: true
        host_organization_lineage:
          type: array
          items:
            type: string
        type:
          type: string
          description: The [source type](/api-reference/source-types)
    DehydratedAuthor:
      type: object
      description: >-
        [Dehydrated Author](/api-reference/authors#the-dehydratedauthor-object)
        — reduced-field version used in nested contexts
      properties:
        id:
          type: string
        display_name:
          type: string
        orcid:
          type: string
          nullable: true
    DehydratedInstitution:
      type: object
      description: >-
        [Dehydrated
        Institution](/api-reference/institutions#the-dehydratedinstitution-object)
        — reduced-field version used in nested contexts
      properties:
        id:
          type: string
        display_name:
          type: string
        ror:
          type: string
          nullable: true
        country_code:
          type: string
          nullable: true
          description: '[Country](/api-reference/countries) code'
        type:
          type: string
          description: The [institution type](/api-reference/institution-types)
        lineage:
          type: array
          items:
            type: string
  responses:
    NotFound:
      description: Entity not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    RateLimited:
      description: Rate limit exceeded
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
  securitySchemes:
    apiKey:
      type: apiKey
      in: query
      name: api_key
      description: >-
        Your OpenAlex API key. Get a free key at
        https://openalex.org/settings/api

````

Built with [Mintlify](https://mintlify.com).