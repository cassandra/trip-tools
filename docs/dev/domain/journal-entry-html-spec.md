# Journal Entry HTML Structure Specification

**Version:** 1.0
**Last Updated:** 2025-11-19
**Status:** Draft

## 1. Overview

### Purpose
This document defines the canonical HTML structure for journal entry content in the Trip Tools journal editor. The specification ensures:
- Predictable, limited HTML structure
- Support for image drag-and-drop operations
- Compatibility with native contenteditable features
- Clean, maintainable content storage

### Design Goals
1. **Strict structure**: Deliberately limit allowed HTML to prevent complexity
2. **Drag-and-drop clarity**: Clear rules for where images can be placed
3. **Native editing support**: Work with browser's native contenteditable operations
4. **Normalization target**: Well-defined structure for automatic cleanup

**Key Principle:** Text content added by user is never removed or lost. Regardless of the defined normalized HTML structure, all normalization rules must preserve the text content is some form in this structure.  It is better to move the text content to the wrong place than it is to lose the content.

## 2. Top-Level Structure

All content must be direct children of `<div class="journal-contenteditable">` and follow these rules:

### Allowed Top-Level Elements

Only these elements are permitted at the top level:

1. **`<p class="text-block">`** - Text paragraphs with inline content
2. **`<div class="text-block">`** - Block-level formatted content (lists, quotes, code)
3. **`<div class="content-block full-width-image-group">`** - Full-width image containers
4. **`<h1>`, `<h2>`, `<h3>`, `<h4>`, `<h5>`, `<h6>`** - Section headings

### Forbidden at Top Level

- Bare text nodes (must be wrapped in `<p class="text-block">`)
- `<br>` tags (see Section 2.1 for detailed handling)
- `<ul>`, `<ol>`, `<blockquote>`, `<pre>` (must be inside `<div class="text-block">`)
- Any element without proper class attributes (except headings)
- Nested `content-block` or `text-block` elements

### 2.1. Top-Level `<br>` Tag Handling

`<br>` tags at the top level indicate the user pressed Enter in contenteditable, signaling intent to create a paragraph break. The normalization behavior depends on surrounding content.

**Key Principle:** Users **cannot** control vertical spacing between paragraphs. All spacing is controlled by CSS. `<br>` tags are treated as paragraph separators, never as whitespace generators.

#### Handling Rules

**1. `<br>` between existing paragraphs (redundant):**
```html
<!-- INVALID: br between already-separated paragraphs -->
<p class="text-block">Paragraph one</p>
<br>
<p class="text-block">Paragraph two</p>

<!-- Normalized: strip the br (paragraphs already separated) -->
<p class="text-block">Paragraph one</p>
<p class="text-block">Paragraph two</p>
```
**Action:** Strip `<br>` (already have paragraph separation)

**2. `<br>` with naked text before:**
```html
<!-- INVALID: naked text then br -->
Some text here
<br>
<p class="text-block">Next paragraph</p>

<!-- Normalized: wrap text before br in paragraph -->
<p class="text-block">Some text here</p>
<p class="text-block">Next paragraph</p>
```
**Action:** Wrap text before `<br>` in `<p class="text-block">`, strip `<br>`

**3. `<br>` with naked text after:**
```html
<!-- INVALID: br then naked text -->
<p class="text-block">Previous paragraph</p>
<br>
Some text here

<!-- Normalized: wrap text after br in paragraph -->
<p class="text-block">Previous paragraph</p>
<p class="text-block">Some text here</p>
```
**Action:** Wrap text after `<br>` in `<p class="text-block">`, strip `<br>`

**4. `<br>` with naked text on BOTH sides (paragraph separator):**
```html
<!-- INVALID: text, br, text -->
Text before the break
<br>
Text after the break

<!-- Normalized: create TWO paragraphs (br acts as separator) -->
<p class="text-block">Text before the break</p>
<p class="text-block">Text after the break</p>
```
**Action:** `<br>` acts as paragraph boundary, create two paragraphs

**5. Multiple consecutive `<br>` tags:**
```html
<!-- INVALID: multiple br between text -->
First paragraph text
<br><br><br>
Second paragraph text

<!-- Normalized: treat as single paragraph break -->
<p class="text-block">First paragraph text</p>
<p class="text-block">Second paragraph text</p>
```
**Action:** Multiple `<br>` = single paragraph break (do NOT create empty paragraphs)

**6. `<br>` inside a paragraph (ALLOWED for line breaks):**
```html
<!-- VALID: br inside paragraph creates line break -->
<p class="text-block">
  Line one<br>
  Line two<br>
  Line three
</p>
```
**Action:** Leave as-is (this is valid and intentional)

**7. Trailing `<br>` with no content after:**
```html
<!-- INVALID: br at end of document -->
<p class="text-block">Last paragraph</p>
<br>

<!-- Normalized: strip br, add cursor placeholder -->
<p class="text-block">Last paragraph</p>
<p class="text-block"><br></p>  <!-- Single empty paragraph for cursor positioning -->
```
**Action:** Strip trailing `<br>`, ensure one empty paragraph for cursor

#### Normalization Algorithm

For each top-level `<br>` encountered:

1. **Examine content before:** Text node? Element? Nothing?
2. **Examine content after:** Text node? Element? Nothing?
3. **Apply transformation:**
   - If (text before AND text after): Create two paragraphs, `<br>` is separator
   - Else if (text before, no text after): Wrap text before, strip `<br>`
   - Else if (text after, no text before): Strip `<br>`, wrap text after
   - Else (no text on either side): Strip `<br>` (redundant)
4. **Consolidate consecutive `<br>` tags:** Treat as single separator, never create empty paragraphs

**Result:** No user control over vertical spacing. Paragraph spacing controlled entirely by CSS (`margin-bottom` on `.text-block`).

### Structure Example

```html
<div class="journal-contenteditable">
  <h2>Section Title</h2>
  <p class="text-block">A paragraph with some text.</p>
  <div class="text-block">
    <ul>
      <li>List item one</li>
      <li>List item two</li>
    </ul>
  </div>
  <div class="content-block full-width-image-group">
    <span class="trip-image-wrapper" data-layout="full-width">...</span>
  </div>
  <p class="text-block">Another paragraph.</p>
</div>
```

## 3. Text Blocks: `<p class="text-block">`

### Purpose
Contain inline text content with optional formatting and float-right images.

### Allowed Content
- Text nodes
- Inline formatting: `<strong>`, `<b>`, `<em>`, `<i>`, `<u>`, `<s>`, `<code>`
- Links: `<a href="...">`
- Images (float-right only): `<span class="trip-image-wrapper" data-layout="float-right">`
- Line breaks: `<br>` (within the paragraph)
- Other inline elements as permitted by HTML sanitizer

### Forbidden Content
- Block-level elements: `<div>`, `<p>`, `<ul>`, `<ol>`, `<blockquote>`, `<pre>`, `<h1-h6>`
- Nested `text-block` or `content-block` elements
- Full-width images

### Constraints
- Must contain at least some text content (after stripping HTML tags)
- Cannot be empty (will be removed during normalization)
- If only contains `<img>` tags (no text), converted to `full-width-image-group`

### Float-Right Image Placement

Float-right images are inserted at the **beginning** of the paragraph using DOM `prepend()`:

```html
<p class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">
    <img src="..." class="trip-image" data-uuid="...">
  </span>
  Text content flows naturally around the floated image.
</p>
```

**CSS Behavior:**
- Image uses `float: right` with `margin: 0 0 1rem 1rem`
- Paragraph gets `has-float-image` class which applies `clear: both`
- Text from subsequent paragraphs (without `has-float-image`) wraps around the floated image

### Examples

```html
<!-- Valid: paragraph with float-right image -->
<p class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">
    <img src="..." class="trip-image" data-uuid="...">
    <span class="trip-image-caption">Photo caption</span>
  </span>
  This is <strong>bold text</strong> that flows around the image.
</p>

<!-- Valid: plain paragraph -->
<p class="text-block">Simple text without images.</p>

<!-- Invalid: block element inside paragraph -->
<p class="text-block">
  <div>Not allowed</div>
</p>

<!-- Invalid: empty paragraph -->
<p class="text-block"></p>

<!-- Invalid: only images, no text -->
<p class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">...</span>
</p>
```

## 4. Block Text Elements: `<div class="text-block">`

### Purpose
Contain block-level formatted content: lists, blockquotes, and code blocks.

### Allowed Content

**Exactly ONE of the following block-level elements:**

1. **Unordered List:** `<ul><li>...</li></ul>`
2. **Ordered List:** `<ol><li>...</li></ol>`
3. **Blockquote:** `<blockquote><p>...</p></blockquote>`
4. **Code Block:** `<pre><code>...</code></pre>` or `<pre>...</pre>`

**Plus optional float-right images** (same as `<p class="text-block">`)

### Forbidden Content
- Multiple block elements in one `div.text-block`
- Inline content directly in the div (must be inside `<ul>`, `<ol>`, `<blockquote>`, or `<pre>`)
- Headings `<h1-h6>` (must be split to top level - see Section 10)
- Full-width images

### Constraints
- Must contain at least some text content
- Cannot be empty (will be removed during normalization)
- List items (`<li>`) and blockquote paragraphs can contain inline formatting
- Float-right images are inserted at **beginning** of the div (same as `<p>`)

### Float-Right Image Placement

Float-right images work the same way as in `<p class="text-block">`:

```html
<div class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">
    <img src="..." class="trip-image" data-uuid="...">
  </span>
  <ul>
    <li>List item one flows around the image</li>
    <li>List item two continues flowing</li>
  </ul>
</div>
```

### Examples

```html
<!-- Valid: unordered list -->
<div class="text-block">
  <ul>
    <li>First item</li>
    <li>Second item with <em>emphasis</em></li>
  </ul>
</div>

<!-- Valid: list with float-right image -->
<div class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">
    <img src="..." class="trip-image" data-uuid="...">
  </span>
  <ul>
    <li>List flows around image</li>
    <li>Just like paragraph text</li>
  </ul>
</div>

<!-- Valid: blockquote with multiple paragraphs -->
<div class="text-block">
  <blockquote>
    <p>First paragraph of quote.</p>
    <p>Second paragraph of quote.</p>
  </blockquote>
</div>

<!-- Valid: code block -->
<div class="text-block">
  <pre><code>function example() {
  return true;
}</code></pre>
</div>

<!-- Invalid: multiple block elements -->
<div class="text-block">
  <ul><li>List</li></ul>
  <p>Paragraph</p>
</div>

<!-- Invalid: heading inside div.text-block -->
<div class="text-block">
  <ul><li>Item</li></ul>
  <h2>Not allowed here</h2>
  <ul><li>Another item</li></ul>
</div>
```

## 5. Section Headings: `<h1>` through `<h6>`

### Purpose
Section titles and document structure.

### Allowed Content
- Text nodes
- Inline formatting: `<strong>`, `<b>`, `<em>`, `<i>`, `<u>`, `<s>`
- Links: `<a href="...">`

### Forbidden Content
- Images (float-right or full-width)
- Block-level elements
- `<br>` tags (headings should be single line)

### Constraints
- Must contain text content
- Cannot be empty (will be removed during normalization)
- No class attribute required (unlike text-blocks)
- **Cannot appear inside `.text-block`** - see Section 10 for split behavior

### Examples

```html
<!-- Valid -->
<h2>Chapter Title</h2>
<h3>Subsection with <em>emphasis</em></h3>

<!-- Invalid: image in heading -->
<h2>Title <span class="trip-image-wrapper">...</span></h2>

<!-- Invalid: empty heading -->
<h2></h2>

<!-- Invalid: heading inside text-block -->
<div class="text-block">
  <ul><li>Item</li></ul>
  <h3>Section</h3>  <!-- NOT ALLOWED -->
</div>
```

## 6. Image Blocks: `<div class="content-block full-width-image-group">`

### Purpose
Container for full-width images positioned between text blocks.

### Allowed Content
- One or more `<span class="trip-image-wrapper" data-layout="full-width">` elements
- Each wrapper contains:
  - `<img class="trip-image" data-uuid="..." src="...">`
  - Optional `<span class="trip-image-caption">...</span>`

### Forbidden Content
- Text nodes
- Text blocks or paragraphs
- Float-right images
- Other block-level content

### Constraints
- Must contain at least one image
- Empty image groups removed during normalization
- Multiple consecutive full-width images can be grouped together

### Examples

```html
<!-- Valid: single image -->
<div class="content-block full-width-image-group">
  <span class="trip-image-wrapper" data-layout="full-width">
    <img src="/media/..." alt="..." class="trip-image" data-uuid="...">
    <span class="trip-image-caption">Photo caption</span>
  </span>
</div>

<!-- Valid: multiple images grouped -->
<div class="content-block full-width-image-group">
  <span class="trip-image-wrapper" data-layout="full-width">
    <img src="/media/1.jpg" class="trip-image" data-uuid="...">
  </span>
  <span class="trip-image-wrapper" data-layout="full-width">
    <img src="/media/2.jpg" class="trip-image" data-uuid="...">
  </span>
</div>

<!-- Invalid: empty group -->
<div class="content-block full-width-image-group"></div>

<!-- Invalid: text content -->
<div class="content-block full-width-image-group">
  Some text here
</div>
```

## 7. Float-Right Image Flow Behavior

### CSS Float Mechanism

Float-right images use standard CSS `float: right` behavior with special clearing rules:

```css
/* Float-right image wrapper */
.trip-image-wrapper[data-layout="float-right"] {
  float: right;
  margin: 0 0 1rem 1rem;  /* bottom and left margin */
  max-width: 25%;
}

/* Container with float-right image clears previous floats */
.has-float-image {
  clear: both;
}
```

### Text Flow Around Floated Images

When a text block contains a float-right image:
1. The image floats to the right
2. Text within that block flows around the image
3. **Subsequent blocks WITHOUT float-right images continue to flow around the image**
4. Blocks WITH their own float-right images clear previous floats and start below

### Flow Example

```html
<div class="journal-contenteditable">
  <!-- Paragraph 1: has float-right image -->
  <p class="text-block has-float-image">
    <span class="trip-image-wrapper" data-layout="float-right">
      <img src="tall-image.jpg" class="trip-image" data-uuid="...">
    </span>
    This is a short paragraph with a tall image floating right.
  </p>

  <!-- Paragraph 2: NO float-right image, flows around image from Paragraph 1 -->
  <p class="text-block">
    This longer paragraph text will fill the space to the left
    of the image from the previous paragraph, because the
    previous paragraph's text was too short to fill that space.
    The text wraps naturally using standard CSS float behavior.
  </p>

  <!-- Paragraph 3: has its own float-right image, clears previous floats -->
  <p class="text-block has-float-image">
    <span class="trip-image-wrapper" data-layout="float-right">
      <img src="another-image.jpg" class="trip-image" data-uuid="...">
    </span>
    This paragraph starts BELOW the first image because it has
    its own float-right image (has-float-image class applies clear: both).
  </p>
</div>
```

### Visual Layout

```
┌───────────────────────────────────────┐
│ Text text text text      ┌─────────┐ │ ← Paragraph 1 (has-float-image)
│ text text.               │  Image  │ │
│                          │    1    │ │
│ This longer paragraph    │         │ │ ← Paragraph 2 (flows around)
│ fills the space to the   │         │ │
│ left of the image from   └─────────┘ │
│ the previous paragraph.              │
│                                      │
│ This paragraph clears    ┌─────────┐ │ ← Paragraph 3 (has-float-image)
│ and starts below.        │  Image  │ │   (clear: both applied)
│                          │    2    │ │
└──────────────────────────┴─────────┴─┘
```

## 8. Drag-and-Drop Behavior

### Drop Target: `.text-block` (p or div)

**Result:** Insert image as **float-right** within the text block

**Rules:**
- Works for both `<p class="text-block">` and `<div class="text-block">`
- Image inserted at **beginning** of container using `prepend()`
- Container gets `has-float-image` class added automatically
- Image uses `<span class="trip-image-wrapper" data-layout="float-right">`
- Multiple float-right images per text block allowed (maximum 2 enforced by JavaScript)

**Example:**

```html
<!-- Before drop -->
<div class="text-block">
  <ul>
    <li>List item one</li>
    <li>List item two</li>
  </ul>
</div>

<!-- After dropping image on this div -->
<div class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">
    <img src="..." class="trip-image" data-uuid="...">
  </span>
  <ul>
    <li>List item one</li>
    <li>List item two</li>
  </ul>
</div>
```

### Drop Target: `.full-width-image-group`

**Result:** Add image to the **existing** full-width group

**Rules:**
- Image appended to the group's children
- Maintains `data-layout="full-width"`
- Multiple images accumulate in the group

**Example:**

```html
<!-- Before drop -->
<div class="content-block full-width-image-group">
  <span class="trip-image-wrapper" data-layout="full-width">
    <img src="image1.jpg" class="trip-image" data-uuid="...">
  </span>
</div>

<!-- After dropping another image -->
<div class="content-block full-width-image-group">
  <span class="trip-image-wrapper" data-layout="full-width">
    <img src="image1.jpg" class="trip-image" data-uuid="...">
  </span>
  <span class="trip-image-wrapper" data-layout="full-width">
    <img src="image2.jpg" class="trip-image" data-uuid="...">
  </span>
</div>
```

### Drop Target: Between `.content-block` elements

**Result:** Create **new** `<div class="content-block full-width-image-group">`

**Rules:**
- Inserted at the drop position between blocks
- Contains single image initially
- Subsequent drops on this group can add more images

**Example:**

```html
<!-- Before drop -->
<div class="journal-contenteditable">
  <p class="text-block">Text before</p>
  <!-- DROP HERE -->
  <p class="text-block">Text after</p>
</div>

<!-- After drop -->
<div class="journal-contenteditable">
  <p class="text-block">Text before</p>
  <div class="content-block full-width-image-group">
    <span class="trip-image-wrapper" data-layout="full-width">
      <img src="..." class="trip-image" data-uuid="...">
    </span>
  </div>
  <p class="text-block">Text after</p>
</div>
```

## 9. Normalization Rules

The HTML structure must be normalized automatically to maintain compliance with this specification.

### Trigger Points
- After toolbar operations (list, heading, indent, format)
- After paste events
- Before autosave
- Before final save
- On initial load (as a sanity check and to "migrate" to new any new normalization logic)

### Normalization Operations

#### 1. Wrap Unwrapped Content

**Rule:** All top-level content must be in proper containers

```html
<!-- Before -->
<div class="journal-contenteditable">
  Naked text
  <br><br>
  More text
</div>

<!-- After -->
<div class="journal-contenteditable">
  <p class="text-block">Naked text</p>
  <p class="text-block">More text</p>
</div>
```

#### 2. Split Multi-Element Text Blocks

**Rule:** One block element per `div.text-block`, one paragraph per `p.text-block`

```html
<!-- Before -->
<div class="text-block">
  <ul><li>List</li></ul>
  <blockquote><p>Quote</p></blockquote>
</div>

<!-- After -->
<div class="text-block"><ul><li>List</li></ul></div>
<div class="text-block"><blockquote><p>Quote</p></blockquote></div>
```

**Note:** If a `<p class="text-block">` contains multiple paragraphs created by the browser:

```html
<!-- Before (browser created multiple <p> inside one) -->
<div class="text-block">
  <p>First paragraph</p>
  <p>Second paragraph</p>
</div>

<!-- After (split into separate text-blocks) -->
<p class="text-block">First paragraph</p>
<p class="text-block">Second paragraph</p>
```

#### 3. Remove Empty Blocks

**Rule:** Delete blocks with no meaningful content

```html
<!-- Before -->
<div class="journal-contenteditable">
  <p class="text-block"></p>
  <p class="text-block">   </p>
  <div class="text-block"><ul></ul></div>
  <p class="text-block">Real content</p>
  <p class="text-block"></p>
  <p class="text-block"></p>
</div>

<!-- After -->
<div class="journal-contenteditable">
  <p class="text-block">Real content</p>
  <p class="text-block"><br></p>  <!-- Keep ONE trailing empty for cursor -->
</div>
```

#### 4. Convert Image-Only Text Blocks

**Rule:** Text blocks with only images (no text) become full-width groups

```html
<!-- Before -->
<p class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">...</span>
</p>

<!-- After -->
<div class="content-block full-width-image-group">
  <span class="trip-image-wrapper" data-layout="full-width">...</span>
</div>
```

#### 5. Unwrap Invalid Nesting

**Rule:** Block elements must be properly contained

```html
<!-- Before: list not wrapped -->
<div class="journal-contenteditable">
  <ul><li>Item</li></ul>
</div>

<!-- After -->
<div class="journal-contenteditable">
  <div class="text-block"><ul><li>Item</li></ul></div>
</div>
```

#### 6. Strip Invalid Top-Level Elements

**Rule:** Remove or convert disallowed top-level elements

```html
<!-- Before -->
<div class="journal-contenteditable">
  <div>Random div</div>
  <span>Random span</span>
  <br>
</div>

<!-- After -->
<div class="journal-contenteditable">
  <p class="text-block">Random div</p>
  <p class="text-block">Random span</p>
</div>
```

## 10. Heading Split Behavior

### Rule
Headings (`<h1>` through `<h6>`) **cannot** appear inside `.text-block` elements. If found during normalization, the text-block must be split.

### Split Logic

The number of resulting top-level elements depends on content position:

1. **Content before AND after heading:** Split into **3 elements**
2. **Content only before OR only after:** Split into **2 elements**
3. **Heading alone in block:** Unwrap to **1 element** (just the heading at top level)

### Examples

#### Case 1: Content Before AND After Heading (3 elements)

```html
<!-- Before (INVALID) -->
<div class="text-block">
  <ul><li>Item before</li></ul>
  <h2>Section Title</h2>
  <ul><li>Item after</li></ul>
</div>

<!-- After normalization (3 elements) -->
<div class="text-block"><ul><li>Item before</li></ul></div>
<h2>Section Title</h2>
<div class="text-block"><ul><li>Item after</li></ul></div>
```

#### Case 2: Content Only Before Heading (2 elements)

```html
<!-- Before (INVALID) -->
<div class="text-block">
  <blockquote><p>Quote text</p></blockquote>
  <h3>Next Section</h3>
</div>

<!-- After normalization (2 elements) -->
<div class="text-block"><blockquote><p>Quote text</p></blockquote></div>
<h3>Next Section</h3>
```

#### Case 3: Content Only After Heading (2 elements)

```html
<!-- Before (INVALID) -->
<div class="text-block">
  <h4>Subsection</h4>
  <ul><li>Item one</li><li>Item two</li></ul>
</div>

<!-- After normalization (2 elements) -->
<h4>Subsection</h4>
<div class="text-block"><ul><li>Item one</li><li>Item two</li></ul></div>
```

#### Case 4: Heading Alone (1 element)

```html
<!-- Before (INVALID) -->
<div class="text-block">
  <h2>Standalone Title</h2>
</div>

<!-- After normalization (1 element) -->
<h2>Standalone Title</h2>
```

#### Case 5: Multiple Headings (split each)

```html
<!-- Before (INVALID) -->
<div class="text-block">
  <ul><li>List</li></ul>
  <h2>Section 1</h2>
  <blockquote><p>Quote</p></blockquote>
  <h3>Section 2</h3>
  <pre><code>Code</code></pre>
</div>

<!-- After normalization (5 elements) -->
<div class="text-block"><ul><li>List</li></ul></div>
<h2>Section 1</h2>
<div class="text-block"><blockquote><p>Quote</p></blockquote></div>
<h3>Section 2</h3>
<div class="text-block"><pre><code>Code</code></pre></div>
```

### Heading Split with Float-Right Images

If the text-block contains a float-right image, it stays with the first content block:

```html
<!-- Before (INVALID) -->
<div class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">...</span>
  <ul><li>List item</li></ul>
  <h2>Section Break</h2>
  <ul><li>After heading</li></ul>
</div>

<!-- After normalization (3 elements, image stays with first) -->
<div class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">...</span>
  <ul><li>List item</li></ul>
</div>
<h2>Section Break</h2>
<div class="text-block"><ul><li>After heading</li></ul></div>
```

## 11. Complete Valid Examples

### Example 1: Article with Mixed Content

```html
<div class="journal-contenteditable">
  <h1>Day 5: Exploring the City</h1>

  <p class="text-block">We started the morning with coffee at a local café.</p>

  <div class="content-block full-width-image-group">
    <span class="trip-image-wrapper" data-layout="full-width">
      <img src="cafe.jpg" class="trip-image" data-uuid="abc-123">
      <span class="trip-image-caption">Morning coffee</span>
    </span>
  </div>

  <p class="text-block has-float-image">
    <span class="trip-image-wrapper" data-layout="float-right">
      <img src="building.jpg" class="trip-image" data-uuid="def-456">
    </span>
    The architecture was stunning. We spent hours just walking around.
  </p>

  <h2>Afternoon Activities</h2>

  <div class="text-block">
    <ul>
      <li>Visited the museum</li>
      <li>Had lunch at the market</li>
      <li>Walked through the park</li>
    </ul>
  </div>

  <div class="text-block">
    <blockquote>
      <p>This city has a way of surprising you at every turn.</p>
    </blockquote>
  </div>

  <p class="text-block">Can't wait to see what tomorrow brings!</p>
</div>
```

### Example 2: List with Float-Right Image

```html
<div class="journal-contenteditable">
  <h3>Packing Checklist</h3>

  <div class="text-block has-float-image">
    <span class="trip-image-wrapper" data-layout="float-right">
      <img src="backpack.jpg" class="trip-image" data-uuid="ghi-789">
      <span class="trip-image-caption">Travel backpack</span>
    </span>
    <ul>
      <li>Passport and travel documents</li>
      <li>Comfortable walking shoes</li>
      <li>Weather-appropriate clothing</li>
      <li>Camera and chargers</li>
      <li>First aid kit</li>
    </ul>
  </div>

  <p class="text-block">Don't forget to check the weather forecast!</p>
</div>
```

### Example 3: Code Block and Blockquote

```html
<div class="journal-contenteditable">
  <h3>Setup Instructions</h3>

  <div class="text-block">
    <ol>
      <li>Install the dependencies</li>
      <li>Configure the settings</li>
      <li>Run the application</li>
    </ol>
  </div>

  <p class="text-block">Here's the configuration file:</p>

  <div class="text-block">
    <pre><code>{
  "setting": "value",
  "enabled": true
}</code></pre>
  </div>

  <div class="text-block">
    <blockquote>
      <p>Remember to backup your data before making changes.</p>
    </blockquote>
  </div>
</div>
```

### Example 4: Float Flow Across Multiple Paragraphs

```html
<div class="journal-contenteditable">
  <h2>The Hike</h2>

  <p class="text-block has-float-image">
    <span class="trip-image-wrapper" data-layout="float-right">
      <img src="mountain.jpg" class="trip-image" data-uuid="jkl-012">
      <span class="trip-image-caption">Mountain vista</span>
    </span>
    We set out early in the morning.
  </p>

  <!-- This paragraph flows around the image from above -->
  <p class="text-block">
    The trail was steep but the views were incredible. Every turn
    revealed new vistas of the valley below. We stopped frequently
    to catch our breath and take photos.
  </p>

  <!-- This paragraph also flows around the image if it's still tall enough -->
  <p class="text-block">
    By noon we reached the summit and enjoyed a well-deserved lunch
    while taking in the panoramic views.
  </p>
</div>
```

## 12. Invalid Examples (What Normalization Fixes)

### Invalid: Multiple Paragraphs in One Element

```html
<!-- INVALID -->
<div class="text-block">
  <p>First</p>
  <p>Second</p>
</div>

<!-- Normalized to: -->
<p class="text-block">First</p>
<p class="text-block">Second</p>
```

### Invalid: Images in Headings

```html
<!-- INVALID -->
<h2>Title <span class="trip-image-wrapper">...</span></h2>

<!-- Normalized to: -->
<h2>Title</h2>
<div class="content-block full-width-image-group">
  <span class="trip-image-wrapper" data-layout="full-width">...</span>
</div>
```

### Invalid: Naked Text and br Tags

```html
<!-- INVALID -->
<div class="journal-contenteditable">
  Some text
  <br><br>
  More text
</div>

<!-- Normalized to: -->
<div class="journal-contenteditable">
  <p class="text-block">Some text</p>
  <p class="text-block">More text</p>
</div>
```

### Invalid: Empty Proliferation

```html
<!-- INVALID -->
<div class="journal-contenteditable">
  <p></p><p></p><p>Content</p><p></p><p></p>
</div>

<!-- Normalized to: -->
<div class="journal-contenteditable">
  <p class="text-block">Content</p>
  <p class="text-block"><br></p>  <!-- One trailing empty -->
</div>
```

### Invalid: Heading Inside Text Block

```html
<!-- INVALID -->
<div class="text-block">
  <ul><li>Before</li></ul>
  <h2>Middle</h2>
  <ul><li>After</li></ul>
</div>

<!-- Normalized to: -->
<div class="text-block"><ul><li>Before</li></ul></div>
<h2>Middle</h2>
<div class="text-block"><ul><li>After</li></ul></div>
```

### Invalid: Image-Only Text Block

```html
<!-- INVALID -->
<p class="text-block has-float-image">
  <span class="trip-image-wrapper" data-layout="float-right">...</span>
</p>

<!-- Normalized to: -->
<div class="content-block full-width-image-group">
  <span class="trip-image-wrapper" data-layout="full-width">...</span>
</div>
```

## 13. Edge Cases

### Empty Editor
```html
<div class="journal-contenteditable">
  <p class="text-block"><br></p>
</div>
```

### Single Heading Only
```html
<div class="journal-contenteditable">
  <h2>Title</h2>
  <p class="text-block"><br></p>  <!-- Cursor positioning -->
</div>
```

### All Images, No Text
```html
<div class="journal-contenteditable">
  <div class="content-block full-width-image-group">
    <span class="trip-image-wrapper" data-layout="full-width">...</span>
  </div>
  <div class="content-block full-width-image-group">
    <span class="trip-image-wrapper" data-layout="full-width">...</span>
  </div>
  <p class="text-block"><br></p>
</div>
```

### Consecutive Full-Width Groups
```html
<div class="journal-contenteditable">
  <p class="text-block">Some text before images.</p>

  <div class="content-block full-width-image-group">
    <span class="trip-image-wrapper" data-layout="full-width">...</span>
    <span class="trip-image-wrapper" data-layout="full-width">...</span>
  </div>

  <div class="content-block full-width-image-group">
    <span class="trip-image-wrapper" data-layout="full-width">...</span>
  </div>

  <p class="text-block">Some text after images.</p>
</div>
```

## 14. Implementation Notes

### CSS Requirements

The following CSS must be present for proper float-right behavior:

```css
/* Float-right image wrapper */
.trip-image-wrapper[data-layout="float-right"] {
  float: right;
  margin: 0 0 1rem 1rem;
  max-width: 25%;
}

/* Container with float-right image clears previous floats */
.has-float-image {
  clear: both;
}
```

**Important:** The `.has-float-image` rule must NOT be scoped to `p` only (e.g., NOT `p.has-float-image`) because it needs to work for both `<p class="text-block">` and `<div class="text-block">` containers.

### JavaScript Responsibilities

The journal editor JavaScript must:

1. **Apply `has-float-image` class** to any `.text-block` containing float-right images
2. **Insert float-right images at beginning** of container using `prepend()`
3. **Run normalization** after toolbar operations, paste events, and before save
4. **Enforce maximum 2 float-right images** per text-block
5. **Handle drag-and-drop** according to Section 8 rules

### Backend Sanitization

The HTML sanitizer must allow:
- `<div class="text-block">`
- `<div class="content-block full-width-image-group">`
- `<p class="text-block">`
- `<span class="trip-image-wrapper" data-layout="float-right|full-width">`
- All heading tags `<h1>` through `<h6>`
- Block elements: `<ul>`, `<ol>`, `<blockquote>`, `<pre>`
- Inline elements: `<strong>`, `<b>`, `<em>`, `<i>`, `<u>`, `<s>`, `<code>`, `<a>`

---

**End of Specification**
