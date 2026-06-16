# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the listings dataset for items that match the user's request, size, and budget.

**Input parameters:**
description (str): Item the user is looking for
size (str): Desired size
max_price (float): Maximum budget

**What it returns:**
A list of matching listings containing fields such as id, title, description, size, price, condition, brand, platform, colors, and style tags.

**What happens if it fails or returns nothing:**
Tell the user no matches were found and suggest changing size, price, or keywords. Stop the workflow.

---

### Tool 2: suggest_outfit

**What it does:**
Creates an outfit recommendation using the selected listing and the user's wardrobe.

**Input parameters:**
new_item (dict): Selected listing
wardrobe (dict): User wardrobe data

**What it returns:**
A short outfit suggestion.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, give a generic styling suggestion. Otherwise, ask for more wardrobe information.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short social-style caption based on the outfit and selected item.

**Input parameters:**
outfit (str): Outfit recommendation

**What it returns:**
A fit card caption string.

**What happens if it fails or returns nothing:**
Return a simple fallback caption or ask for complete outfit details.

---

### Tool 4: get_example_wardrobe

**What it does:**
Loads a sample wardrobe for testing or demo purposes.

**Input parameters:**
None.

**What it returns:**
A wardrobe dictionary with example items.

**What happens if it fails or returns nothing:**
Use an empty wardrobe.

---

## Planning Loop

**How does your agent decide which tool to call next?**
- Call search_listings.
- If no results, inform the user and stop.
- Select the top listing and call suggest_outfit.
- Call create_fit_card with the outfit.
- Return the listing, outfit suggestion, and fit card. The workflow ends when all outputs are generated.

---

## State Management

**How does information from one tool get passed to the next?**
The agent stores data in a simple session state object. After search_listings runs, the selected listing is saved as selected_item. That item is passed to suggest_outfit along with the user's wardrobe.

The outfit recommendation is then saved as outfit_suggestion and passed to create_fit_card. The agent tracks:

User search criteria
Search results
Selected listing
User wardrobe
Outfit suggestion
Final fit card

Each tool uses the output of the previous tool until the workflow is complete or an error occurs.

---

## Error Handling

| Tool            | Failure mode                          | Agent response                                                                                                  |
| --------------- | ------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| search_listings | No results match the query            | Tell the user no matching items were found and suggest adjusting keywords, size, or budget. Stop the workflow.  |
| suggest_outfit  | Wardrobe is empty                     | Provide a generic outfit recommendation based on the selected item, or ask the user to add wardrobe items.      |
| create_fit_card | Outfit input is missing or incomplete | Generate a simple fallback caption if possible; otherwise ask for the missing outfit details before continuing. |


---

## Architecture

                          ┌─────────────────┐
                          │   User Input    │
                          │ (item request)  │
                          └────────┬────────┘
                                   │
                                   ▼
                        ┌───────────────────┐
                        │   Planning Loop   │
                        └────────┬──────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     search_listings     │
                    └───────────┬─────────────┘
                                │
                     Results?   │
                     Yes         │ No
                                ▼
                ┌──────────────────────────┐
                │ Save selected_item       │
                │      to state            │
                └───────────┬──────────────┘
                            │
                            ▼
                ┌──────────────────────────┐
                │      suggest_outfit      │
                └───────────┬──────────────┘
                            │
                  Wardrobe? │
                 Yes        │ Empty
                            ▼
                ┌──────────────────────────┐
                │ Save outfit_suggestion   │
                │       to state           │
                └───────────┬──────────────┘
                            │
                            ▼
                ┌──────────────────────────┐
                │      create_fit_card     │
                └───────────┬──────────────┘
                            │
                            ▼
                ┌──────────────────────────┐
                │ Return listing, outfit,  │
                │      and fit card        │
                └──────────────────────────┘


Error Paths

search_listings ──► No results found
                    └─► Tell user to adjust
                        keywords/size/budget
                        and stop

suggest_outfit ──► Empty wardrobe
                   └─► Give generic outfit
                       suggestion or ask
                       for wardrobe items

create_fit_card ──► Missing outfit data
                    └─► Create fallback
                        caption or request
                        missing details


State / Session

state = {
  user_query,
  search_results,
  selected_item,
  wardrobe,
  outfit_suggestion,
  fit_card
}

search_listings  → selected_item
selected_item + wardrobe → suggest_outfit
outfit_suggestion → create_fit_card
fit_card → final response

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
- AI Tool: Claude Code
- Input: Tool specifications from planning.md (inputs, outputs, failure modes), architecture diagram, listings.json, wardrobe_schema.  json, and data_loader.py.
- Expected Output:
search_listings() using load_listings()
suggest_outfit() using the wardrobe schema
create_fit_card() using outfit text
- Verification:
Test search_listings() with matching and non-matching queries.
Test suggest_outfit() with both example and empty wardrobes.
Test create_fit_card() with valid and missing outfit data.
Confirm outputs match the documented return values and error handling.

**Milestone 4 — Planning loop and state management:**
- AI Tool: Claude Code
- Input: Architecture diagram, planning loop description, state management section, tool interfaces, and error-handling table.
- Expected Output:
A planning loop that calls tools in order.
Session state object storing user_query, search_results, selected_item, wardrobe, outfit_suggestion, and fit_card.
Logic for branching on failures and stopping when appropriate.
- Verification:
Run a successful end-to-end example and verify all tools are called in the correct order.
Run a no-results search and confirm the workflow stops after search_listings().
Run with an empty wardrobe and confirm a fallback outfit is produced.
Verify state updates correctly after each tool call and the final response contains the listing, outfit suggestion, and fit card.

---

## A Complete Interaction (Step by Step)

FitFindr first uses search_listings to find clothing items that match what the user wants, using fields like title, description, style tags, size, price, condition, brand, and platform. If it finds matches, it picks the best result and passes that item to suggest_outfit, which uses the user's wardrobe data (items, categories, colors, style tags, and notes) to create an outfit recommendation. After that, create_fit_card turns the outfit suggestion and selected item into a short social-style caption. If search_listings finds no matching listings, FitFindr stops, tells the user how to adjust their search, and does not call suggest_outfit or create_fit_card.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent calls search_listings with:

search_listings(
    description="vintage graphic tee",
    size="M",
    max_price=30.0
)

The tool searches listings using fields such as title, description, style tags, size, and price. It returns matching items and the agent selects the top result.

Returned item:

Vintage Band Tee — Faded Grey
$19
Depop
Size L (boxy fit)

**Step 2:**
The agent saves the selected item to state and calls suggest_outfit.

suggest_outfit(
    new_item=selected_item,
    wardrobe=user_wardrobe
)

The tool uses the user's wardrobe information and returns:

Pair this vintage band tee with your baggy dark-wash jeans and chunky white sneakers for a relaxed 90s streetwear look. Add a black denim jacket for layering.

**Step 3:**
The agent saves the outfit suggestion and calls create_fit_card.

create_fit_card(
    outfit=outfit_suggestion
)

The tool returns:

thrifted this vintage band tee for $19 and it goes perfectly with my baggy jeans, full fit in my stories

**Final output to user:**
Top Match:
Vintage Band Tee — Faded Grey
$19 on Depop
Vintage, graphic tee, grunge, streetwear

How to Style It:
Pair this vintage band tee with your baggy dark-wash jeans and chunky white sneakers for a relaxed 90s streetwear look. Add a black denim jacket for layering.

Fit Card:
thrifted this vintage band tee for $19 and it goes perfectly with my baggy jeans, full fit in my stories
