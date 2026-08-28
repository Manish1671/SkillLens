"""Core CS — DBMS & SQL catalog seed. Assessable skills only; no empty parent."""

from app.core.enums import ActivityKind, Difficulty

CORE_CS_TOPIC_SLUG = "core-cs-dbms"

CORE_CS_TOPIC = {
    "slug": CORE_CS_TOPIC_SLUG,
    "name": "DBMS & SQL",
    "sort_order": 70,
}

CORE_CS_SKILL_SLUGS = (
    "sql-basics",
    "sql-joins",
    "normalization",
    "indexing",
    "transactions",
)

CORE_CS_SKILLS = [
    {
        "slug": "sql-basics",
        "name": "SQL Basics",
        "topic_slug": CORE_CS_TOPIC_SLUG,
        "description": "SELECT, WHERE, aggregation, NULL, and result-set reasoning.",
        "is_foundational": True,
        "sort_order": 200,
    },
    {
        "slug": "sql-joins",
        "name": "SQL Joins",
        "topic_slug": CORE_CS_TOPIC_SLUG,
        "description": "INNER, LEFT, and multi-table join cardinality.",
        "is_foundational": False,
        "sort_order": 210,
    },
    {
        "slug": "normalization",
        "name": "Normalization",
        "topic_slug": CORE_CS_TOPIC_SLUG,
        "description": "Functional dependencies and 1NF/2NF/3NF design trade-offs.",
        "is_foundational": False,
        "sort_order": 220,
    },
    {
        "slug": "indexing",
        "name": "Indexing",
        "topic_slug": CORE_CS_TOPIC_SLUG,
        "description": "B-tree indexes, selectivity, and query-plan trade-offs.",
        "is_foundational": False,
        "sort_order": 230,
    },
    {
        "slug": "transactions",
        "name": "Transactions",
        "topic_slug": CORE_CS_TOPIC_SLUG,
        "description": "ACID, isolation anomalies, and locking vs MVCC intuition.",
        "is_foundational": False,
        "sort_order": 240,
    },
]

CORE_CS_DEPENDENCIES = [
    ("sql-basics", "sql-joins"),
    ("sql-basics", "normalization"),
    ("sql-basics", "indexing"),
    ("sql-basics", "transactions"),
]


def _quiz(
    *,
    slug: str,
    title: str,
    prompt: str,
    difficulty: Difficulty,
    minutes: int,
    skill: str,
    options: list[tuple[str, str]],
    correct: str,
    hints: list[str] | None = None,
    extra_skills: list[tuple[str, str]] | None = None,
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "prompt_md": prompt,
        "difficulty": difficulty,
        "estimated_minutes": minutes,
        "topic_slug": CORE_CS_TOPIC_SLUG,
        "activity_kind": ActivityKind.QUIZ,
        "solution_outline_md": None,
        "quiz_spec": {
            "options": [{"id": option_id, "label": label} for option_id, label in options],
            "correct_option_id": correct,
        },
        "skills": [
            {"skill_slug": skill, "weight": "1.0"},
            *[{"skill_slug": slug_, "weight": weight} for slug_, weight in extra_skills or []],
        ],
        "hints": hints or [],
    }


CORE_CS_PROBLEMS = [
    _quiz(
        slug="sql-select-projection",
        title="SELECT projection vs filtering",
        prompt=(
            "A query is written as:\n\n"
            "SELECT name FROM employees WHERE dept = 'Eng';\n\n"
            "Which statement is accurate?"
        ),
        difficulty=Difficulty.EASY,
        minutes=4,
        skill="sql-basics",
        options=[
            ("a", "WHERE chooses columns; SELECT chooses rows."),
            ("b", "SELECT chooses columns; WHERE chooses rows."),
            ("c", "Both SELECT and WHERE choose columns."),
            ("d", "The query returns every column from employees."),
        ],
        correct="b",
        hints=["Think about the result-set shape: which clause shrinks width vs height?"],
    ),
    _quiz(
        slug="sql-null-comparison",
        title="NULL and equality",
        prompt=(
            "Column manager_id is nullable. What does this predicate return for a row "
            "where manager_id IS NULL?\n\nWHERE manager_id = 10"
        ),
        difficulty=Difficulty.EASY,
        minutes=4,
        skill="sql-basics",
        options=[
            ("a", "TRUE, because NULL is treated as 0."),
            ("b", "FALSE, so the row is excluded."),
            ("c", "UNKNOWN, so the row is excluded from the WHERE result."),
            ("d", "TRUE, because NULL equals any value in SQL."),
        ],
        correct="c",
    ),
    _quiz(
        slug="sql-count-nulls",
        title="COUNT and NULL",
        prompt=(
            "Table t has three rows with values 1, NULL, and 2 in column x.\n\n"
            "What do COUNT(*) and COUNT(x) return?"
        ),
        difficulty=Difficulty.EASY,
        minutes=4,
        skill="sql-basics",
        options=[
            ("a", "COUNT(*) = 3 and COUNT(x) = 3"),
            ("b", "COUNT(*) = 3 and COUNT(x) = 2"),
            ("c", "COUNT(*) = 2 and COUNT(x) = 2"),
            ("d", "COUNT(*) = 2 and COUNT(x) = 3"),
        ],
        correct="b",
        hints=["COUNT(*) counts rows. COUNT(column) skips NULLs."],
    ),
    _quiz(
        slug="sql-group-by-having",
        title="GROUP BY vs HAVING",
        prompt=(
            "You need departments whose average salary exceeds 120,000. "
            "Where does that predicate belong?"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="sql-basics",
        options=[
            ("a", "In WHERE, because averages are computed before grouping."),
            ("b", "In HAVING, because it filters groups after aggregation."),
            ("c", "In SELECT, as a boolean column."),
            ("d", "In ORDER BY only."),
        ],
        correct="b",
    ),
    _quiz(
        slug="sql-distinct-vs-group",
        title="DISTINCT vs GROUP BY",
        prompt=(
            "You need unique customer_id values and no aggregates. Which is the best description?"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="sql-basics",
        options=[
            ("a", "SELECT DISTINCT customer_id is sufficient; GROUP BY is for aggregation."),
            ("b", "GROUP BY is required even without aggregates."),
            ("c", "DISTINCT and GROUP BY always produce different cardinalities."),
            ("d", "You must use a window function."),
        ],
        correct="a",
    ),
    _quiz(
        slug="sql-inner-join-drop",
        title="INNER JOIN unmatched rows",
        prompt=(
            "orders has 100 rows. customers has 80 rows. 10 orders have a customer_id "
            "that does not exist in customers.\n\n"
            "SELECT * FROM orders INNER JOIN customers ON orders.customer_id = customers.id\n\n"
            "How many result rows at minimum, assuming remaining keys match one-to-one?"
        ),
        difficulty=Difficulty.EASY,
        minutes=5,
        skill="sql-joins",
        options=[
            ("a", "100"),
            ("b", "90"),
            ("c", "80"),
            ("d", "10"),
        ],
        correct="b",
        extra_skills=[("sql-basics", "0.40")],
        hints=["INNER JOIN keeps only matching keys. Orphan orders disappear."],
    ),
    _quiz(
        slug="sql-left-join-null",
        title="LEFT JOIN null-extended rows",
        prompt=(
            "SELECT c.id, o.id\n"
            "FROM customers c\n"
            "LEFT JOIN orders o ON o.customer_id = c.id\n\n"
            "A customer with no orders appears as:"
        ),
        difficulty=Difficulty.EASY,
        minutes=5,
        skill="sql-joins",
        options=[
            ("a", "The customer is omitted."),
            ("b", "One row with c.id populated and o.id NULL."),
            ("c", "One row with both ids equal to 0."),
            ("d", "A Cartesian product of all orders."),
        ],
        correct="b",
    ),
    _quiz(
        slug="sql-join-filter-on",
        title="Predicate in ON vs WHERE with LEFT JOIN",
        prompt=(
            "FROM customers c LEFT JOIN orders o ON o.customer_id = c.id AND o.status = 'open'\n"
            "versus adding AND o.status = 'open' in WHERE.\n\n"
            "What is the key difference?"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=6,
        skill="sql-joins",
        options=[
            ("a", "They are always identical."),
            (
                "b",
                "ON keeps unmatched customers; WHERE o.status = 'open' "
                "turns the join into an inner join.",
            ),
            ("c", "WHERE preserves unmatched customers; ON drops them."),
            ("d", "ON can only contain equality predicates."),
        ],
        correct="b",
        hints=[
            "A WHERE filter on the right table's non-null column rejects the NULL-extended rows."
        ],
    ),
    _quiz(
        slug="sql-join-fanout",
        title="Join fan-out",
        prompt=(
            "One order has 3 line items. You join orders to line_items on order_id. "
            "How many result rows does that order produce?"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=4,
        skill="sql-joins",
        options=[
            ("a", "1, because the join key is unique on orders."),
            ("b", "3, because each matching line item duplicates the order."),
            ("c", "0, unless you use GROUP BY."),
            ("d", "4, including a header row."),
        ],
        correct="b",
    ),
    _quiz(
        slug="sql-self-join",
        title="Self-join for manager names",
        prompt=(
            "employees(id, name, manager_id). You need each employee with "
            "their manager's name. What is the usual pattern?"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="sql-joins",
        options=[
            ("a", "GROUP BY manager_id without a join."),
            ("b", "Join employees to itself: e.manager_id = m.id."),
            ("c", "UNION ALL of employees and managers tables that do not exist."),
            ("d", "A CROSS JOIN of employees with no predicate."),
        ],
        correct="b",
        extra_skills=[("sql-basics", "0.35")],
    ),
    _quiz(
        slug="nf-repeating-groups",
        title="First normal form",
        prompt=(
            "A table stores phone_numbers as '555-0100,555-0199' in one column. "
            "Which normal form is primarily violated?"
        ),
        difficulty=Difficulty.EASY,
        minutes=4,
        skill="normalization",
        options=[
            ("a", "1NF — atomic values / no repeating groups"),
            ("b", "2NF — partial dependency on a composite key"),
            ("c", "3NF — transitive dependency"),
            ("d", "BCNF — every determinant is a candidate key, only"),
        ],
        correct="a",
    ),
    _quiz(
        slug="nf-partial-dependency",
        title="Partial dependency (2NF)",
        prompt=(
            "Composite key (order_id, product_id). Column product_name depends only on product_id. "
            "This is primarily a violation of:"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="normalization",
        options=[
            ("a", "1NF"),
            ("b", "2NF"),
            ("c", "3NF only, never 2NF"),
            ("d", "There is no dependency problem."),
        ],
        correct="b",
        hints=["2NF forbids non-key attributes depending on part of a composite key."],
    ),
    _quiz(
        slug="nf-transitive",
        title="Transitive dependency (3NF)",
        prompt=(
            "employees(id PK, dept_id, dept_name). dept_name is determined by dept_id, "
            "and dept_id is determined by id. This is a classic:"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="normalization",
        options=[
            ("a", "1NF violation"),
            ("b", "Partial key dependency"),
            ("c", "Transitive dependency (3NF concern)"),
            ("d", "Lossy join"),
        ],
        correct="c",
    ),
    _quiz(
        slug="nf-denorm-tradeoff",
        title="When denormalization is deliberate",
        prompt=(
            "A read-heavy dashboard stores a cached order_total on orders even "
            "though it can be summed from line items. The usual reason is:"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="normalization",
        options=[
            ("a", "To satisfy 3NF more strictly."),
            ("b", "To reduce join cost at the expense of update anomalies."),
            ("c", "Because SQL cannot express SUM."),
            ("d", "To make PRIMARY KEY optional."),
        ],
        correct="b",
    ),
    _quiz(
        slug="idx-equality-btree",
        title="B-tree equality lookup",
        prompt="A B-tree index on users.email is most helpful for which predicate?",
        difficulty=Difficulty.EASY,
        minutes=4,
        skill="indexing",
        options=[
            ("a", "WHERE email = 'a@b.com'"),
            ("b", "WHERE LOWER(email) LIKE '%gmail%' with no expression index"),
            ("c", "WHERE age + 1 = 30 when only email is indexed"),
            ("d", "ORDER BY created_at with no created_at index"),
        ],
        correct="a",
    ),
    _quiz(
        slug="idx-leading-column",
        title="Composite index leading column",
        prompt=(
            "Index (last_name, first_name). Which query can typically use that "
            "index efficiently?"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="indexing",
        options=[
            ("a", "WHERE first_name = 'Ada'"),
            ("b", "WHERE last_name = 'Lovelace'"),
            ("c", "WHERE first_name LIKE '%da'"),
            ("d", "WHERE age = 36"),
        ],
        correct="b",
        hints=["A composite B-tree is ordered from the leftmost column."],
    ),
    _quiz(
        slug="idx-selectivity",
        title="Low-selectivity indexes",
        prompt=(
            "A boolean is_deleted column is true for 0.1% of rows. "
            "When is an index on is_deleted most useful?"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="indexing",
        options=[
            ("a", "Always, because every column should be indexed."),
            ("b", "When queries frequently filter the rare value (is_deleted = true)."),
            ("c", "Only when is_deleted is never used in WHERE."),
            ("d", "Never; booleans cannot be indexed."),
        ],
        correct="b",
    ),
    _quiz(
        slug="idx-write-cost",
        title="Index write overhead",
        prompt="Adding many secondary indexes to a write-heavy table typically:",
        difficulty=Difficulty.EASY,
        minutes=4,
        skill="indexing",
        options=[
            ("a", "Speeds up INSERT/UPDATE/DELETE because indexes replace the heap."),
            ("b", "Slows writes because each change must maintain those indexes."),
            ("c", "Has no effect on writes."),
            ("d", "Removes the need for a primary key."),
        ],
        correct="b",
    ),
    _quiz(
        slug="txn-acid",
        title="ACID durability",
        prompt="After COMMIT returns successfully, a power failure occurs. Durability means:",
        difficulty=Difficulty.EASY,
        minutes=4,
        skill="transactions",
        options=[
            ("a", "The committed changes must survive the crash."),
            ("b", "Uncommitted changes must also survive."),
            ("c", "Isolation level becomes READ UNCOMMITTED."),
            ("d", "The database must drop all indexes."),
        ],
        correct="a",
    ),
    _quiz(
        slug="txn-dirty-read",
        title="Dirty read",
        prompt=(
            "Transaction A updates a row but has not committed. "
            "Transaction B reads that new value. This anomaly is:"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="transactions",
        options=[
            ("a", "A phantom read"),
            ("b", "A dirty read"),
            ("c", "A lost update that already committed"),
            ("d", "A checkpoint"),
        ],
        correct="b",
        hints=["Dirty reads see uncommitted data."],
    ),
    _quiz(
        slug="txn-repeatable-read",
        title="Non-repeatable vs phantom",
        prompt=(
            "In the same transaction, SELECT by primary key returns different column values "
            "on the second read because another transaction committed an UPDATE to that row. "
            "This is:"
        ),
        difficulty=Difficulty.MEDIUM,
        minutes=6,
        skill="transactions",
        options=[
            ("a", "A dirty read"),
            ("b", "A non-repeatable read"),
            ("c", "A phantom read (new row matching a range)"),
            ("d", "A write skew with no reads"),
        ],
        correct="b",
    ),
    _quiz(
        slug="txn-isolation-serializable",
        title="Serializable intent",
        prompt="SERIALIZABLE isolation is designed so concurrent transactions appear as if:",
        difficulty=Difficulty.MEDIUM,
        minutes=5,
        skill="transactions",
        options=[
            ("a", "They ran in some serial order without anomalies from interleaving."),
            ("b", "They always used dirty reads for speed."),
            ("c", "Locks are never taken."),
            ("d", "COMMIT is optional."),
        ],
        correct="a",
    ),
]

CORE_CS_DIAGNOSTIC_SLUGS = [
    "sql-select-projection",
    "sql-inner-join-drop",
    "nf-repeating-groups",
    "idx-equality-btree",
    "txn-acid",
]
