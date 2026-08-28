"""Catalog seed data for SkillLens V1."""

from app.core.enums import Difficulty

TOPICS = [
    {"slug": "arrays-and-hashing", "name": "Arrays & Hashing", "sort_order": 10},
    {"slug": "linked-lists-and-stacks", "name": "Linked Lists & Stacks", "sort_order": 20},
    {"slug": "trees-and-graphs", "name": "Trees & Graphs", "sort_order": 30},
    {"slug": "search", "name": "Search", "sort_order": 40},
    {"slug": "intervals-and-greedy", "name": "Intervals & Greedy", "sort_order": 50},
    {"slug": "dynamic-programming", "name": "Dynamic Programming", "sort_order": 60},
]

SKILLS = [
    {
        "slug": "arrays",
        "name": "Arrays",
        "topic_slug": "arrays-and-hashing",
        "description": "Index traversal, in-place updates, and array boundary reasoning.",
        "is_foundational": True,
        "sort_order": 10,
    },
    {
        "slug": "hashing",
        "name": "Hashing",
        "topic_slug": "arrays-and-hashing",
        "description": "Hash maps and sets for frequency counting and membership checks.",
        "is_foundational": False,
        "sort_order": 20,
    },
    {
        "slug": "two-pointers",
        "name": "Two Pointers",
        "topic_slug": "arrays-and-hashing",
        "description": "Pairwise scanning from both ends or synchronized pointers.",
        "is_foundational": False,
        "sort_order": 30,
    },
    {
        "slug": "sliding-window",
        "name": "Sliding Window",
        "topic_slug": "arrays-and-hashing",
        "description": "Contiguous subarray optimization with expanding and shrinking windows.",
        "is_foundational": False,
        "sort_order": 40,
    },
    {
        "slug": "prefix-sum",
        "name": "Prefix Sum",
        "topic_slug": "arrays-and-hashing",
        "description": "Running totals and range-sum queries over arrays.",
        "is_foundational": False,
        "sort_order": 50,
    },
    {
        "slug": "binary-search",
        "name": "Binary Search",
        "topic_slug": "search",
        "description": "Halving search space on sorted or monotonic structures.",
        "is_foundational": False,
        "sort_order": 60,
    },
    {
        "slug": "linked-lists",
        "name": "Linked Lists",
        "topic_slug": "linked-lists-and-stacks",
        "description": "Pointer manipulation on singly linked nodes.",
        "is_foundational": True,
        "sort_order": 70,
    },
    {
        "slug": "stack",
        "name": "Stack",
        "topic_slug": "linked-lists-and-stacks",
        "description": "LIFO structures for parsing, backtracking, and monotonic patterns.",
        "is_foundational": False,
        "sort_order": 80,
    },
    {
        "slug": "queue",
        "name": "Queue",
        "topic_slug": "linked-lists-and-stacks",
        "description": "FIFO ordering and queue simulation patterns.",
        "is_foundational": False,
        "sort_order": 90,
    },
    {
        "slug": "trees",
        "name": "Trees",
        "topic_slug": "trees-and-graphs",
        "description": "Binary tree traversal, recursion, and structural properties.",
        "is_foundational": True,
        "sort_order": 100,
    },
    {
        "slug": "graphs",
        "name": "Graphs",
        "topic_slug": "trees-and-graphs",
        "description": "Adjacency traversal with BFS and DFS on grids or explicit graphs.",
        "is_foundational": False,
        "sort_order": 110,
    },
    {
        "slug": "intervals",
        "name": "Intervals",
        "topic_slug": "intervals-and-greedy",
        "description": "Sorting and merging ranges on a timeline.",
        "is_foundational": False,
        "sort_order": 120,
    },
    {
        "slug": "greedy",
        "name": "Greedy",
        "topic_slug": "intervals-and-greedy",
        "description": "Locally optimal choices that build a global solution.",
        "is_foundational": False,
        "sort_order": 130,
    },
    {
        "slug": "dynamic-programming",
        "name": "Dynamic Programming",
        "topic_slug": "dynamic-programming",
        "description": "Optimal substructure with memoization or tabulation.",
        "is_foundational": False,
        "sort_order": 140,
    },
]

SKILL_DEPENDENCIES = [
    ("arrays", "hashing"),
    ("arrays", "two-pointers"),
    ("arrays", "prefix-sum"),
    ("arrays", "binary-search"),
    ("two-pointers", "sliding-window"),
    ("linked-lists", "stack"),
    ("linked-lists", "queue"),
    ("trees", "graphs"),
]

PROBLEMS = [
    {
        "slug": "pair-sum-lookup",
        "title": "Pair Sum Lookup",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 20,
        "prompt_md": (
            "Given an integer array `nums` and an integer `target`, return the indices "
            "of two distinct elements whose sum equals `target`. Assume exactly one solution "
            "exists and you may not use the same element twice."
        ),
        "solution_outline_md": "Use a hash map from value to index while scanning once.",
        "skills": [
            {"skill_slug": "hashing", "weight": 1.0},
            {"skill_slug": "arrays", "weight": 0.4},
        ],
        "hints": [
            "A brute-force pair check is O(n^2). Can you remember prior values?",
            "Store each value's index in a hash map as you iterate.",
        ],
    },
    {
        "slug": "contains-duplicate",
        "title": "Contains Duplicate",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 15,
        "prompt_md": "Given an integer array `nums`, return `true` if any value appears at least twice.",
        "solution_outline_md": "Track seen values in a set while iterating.",
        "skills": [{"skill_slug": "hashing", "weight": 1.0}],
        "hints": [
            "Sorting would work but costs O(n log n).",
            "A set gives O(1) membership checks.",
        ],
    },
    {
        "slug": "max-profit-single-trade",
        "title": "Max Profit Single Trade",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 20,
        "prompt_md": (
            "Given prices where `prices[i]` is the stock price on day `i`, choose one buy day "
            "and one later sell day to maximize profit. Return 0 if no profit is possible."
        ),
        "solution_outline_md": "Track minimum price seen so far and best profit.",
        "skills": [{"skill_slug": "arrays", "weight": 1.0}],
        "hints": [
            "You only need the best buy price before each day.",
            "Update running minimum and maximum profit in one pass.",
        ],
    },
    {
        "slug": "product-except-self",
        "title": "Product Except Self",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 30,
        "prompt_md": (
            "Given an integer array `nums`, return an array `answer` where `answer[i]` is the "
            "product of all elements except `nums[i]`. Solve without division and in O(n) time."
        ),
        "solution_outline_md": "Prefix and suffix products in two passes.",
        "skills": [
            {"skill_slug": "prefix-sum", "weight": 1.0},
            {"skill_slug": "arrays", "weight": 0.4},
        ],
        "hints": [
            "Division is disallowed, so build products from left and right accumulators.",
            "First pass stores prefix products; second pass multiplies suffix products.",
        ],
    },
    {
        "slug": "max-subarray-sum",
        "title": "Maximum Subarray Sum",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 25,
        "prompt_md": (
            "Given an integer array `nums`, find the contiguous subarray with the largest sum "
            "and return that sum."
        ),
        "solution_outline_md": "Kadane's algorithm tracks running sum with reset on negativity.",
        "skills": [
            {"skill_slug": "prefix-sum", "weight": 1.0},
            {"skill_slug": "dynamic-programming", "weight": 0.4},
        ],
        "hints": [
            "A subarray can start and end anywhere; brute force is O(n^2).",
            "If the running sum becomes negative, discard it and restart the subarray.",
        ],
    },
    {
        "slug": "merge-intervals",
        "title": "Merge Intervals",
        "topic_slug": "intervals-and-greedy",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 30,
        "prompt_md": (
            "Given an array of intervals `intervals` where `intervals[i] = [start, end]`, merge "
            "all overlapping intervals and return the result."
        ),
        "solution_outline_md": "Sort by start, merge when current start <= previous end.",
        "skills": [{"skill_slug": "intervals", "weight": 1.0}],
        "hints": [
            "Overlapping intervals become obvious after sorting by start time.",
            "Compare each interval's start with the end of the last merged interval.",
        ],
    },
    {
        "slug": "sorted-pair-sum",
        "title": "Sorted Pair Sum",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 25,
        "prompt_md": (
            "Given a 1-indexed sorted array `numbers` and a `target`, return the two indices "
            "(1-indexed) whose values sum to `target`. Exactly one solution exists."
        ),
        "solution_outline_md": "Two pointers from both ends of the sorted array.",
        "skills": [
            {"skill_slug": "two-pointers", "weight": 1.0},
            {"skill_slug": "arrays", "weight": 0.4},
        ],
        "hints": [
            "Sorting is already done; exploit order instead of a hash map.",
            "Move the left pointer up when the sum is too small, right pointer down when too large.",
        ],
    },
    {
        "slug": "three-sum-zero",
        "title": "Three Sum Zero",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 35,
        "prompt_md": (
            "Given integer array `nums`, return all unique triplets `[nums[i], nums[j], nums[k]]` "
            "such that `i != j != k` and the sum is zero."
        ),
        "solution_outline_md": "Sort, fix one index, two-pointer scan for pairs summing to negative fixed value.",
        "skills": [
            {"skill_slug": "two-pointers", "weight": 1.0},
            {"skill_slug": "hashing", "weight": 0.4},
        ],
        "hints": [
            "Fix the first number, then search for a pair that completes the triplet.",
            "Skip duplicate values when advancing pointers to avoid duplicate triplets.",
        ],
    },
    {
        "slug": "longest-unique-substring",
        "title": "Longest Unique Substring",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 30,
        "prompt_md": (
            "Given a string `s`, return the length of the longest substring without repeating "
            "characters."
        ),
        "solution_outline_md": "Sliding window with a map of last seen character indices.",
        "skills": [{"skill_slug": "sliding-window", "weight": 1.0}],
        "hints": [
            "Brute force checks every substring; aim for O(n).",
            "Expand the window and shrink when a duplicate appears inside the window.",
        ],
    },
    {
        "slug": "min-subarray-sum-target",
        "title": "Minimum Subarray Sum Target",
        "topic_slug": "arrays-and-hashing",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 35,
        "prompt_md": (
            "Given an array of positive integers `nums` and integer `target`, return the minimal "
            "length of a contiguous subarray whose sum is greater than or equal to `target`. "
            "Return 0 if none exists."
        ),
        "solution_outline_md": "Sliding window: grow until sum >= target, then shrink from left.",
        "skills": [{"skill_slug": "sliding-window", "weight": 1.0}],
        "hints": [
            "All values are positive, so expanding always increases the sum.",
            "Once the window is valid, try shrinking to find a shorter valid window.",
        ],
    },
    {
        "slug": "classic-binary-search",
        "title": "Classic Binary Search",
        "topic_slug": "search",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 15,
        "prompt_md": (
            "Given a sorted array `nums` and integer `target`, return the index of `target` or "
            "-1 if absent."
        ),
        "solution_outline_md": "Standard binary search with inclusive bounds.",
        "skills": [
            {"skill_slug": "binary-search", "weight": 1.0},
            {"skill_slug": "arrays", "weight": 0.4},
        ],
        "hints": [
            "Linear scan is O(n); the sorted order allows halving the search space.",
            "Maintain `low` and `high` pointers and compare the midpoint to `target`.",
        ],
    },
    {
        "slug": "search-rotated-array",
        "title": "Search Rotated Sorted Array",
        "topic_slug": "search",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 30,
        "prompt_md": (
            "Given a rotated sorted array `nums` with distinct values and integer `target`, "
            "return the index of `target` or -1."
        ),
        "solution_outline_md": "Binary search while identifying which half remains sorted.",
        "skills": [{"skill_slug": "binary-search", "weight": 1.0}],
        "hints": [
            "One half of the array is always sorted after rotation.",
            "Compare `target` against the sorted half before choosing which side to discard.",
        ],
    },
    {
        "slug": "reverse-linked-list",
        "title": "Reverse Linked List",
        "topic_slug": "linked-lists-and-stacks",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 20,
        "prompt_md": (
            "Given the head of a singly linked list, reverse the list and return the new head."
        ),
        "solution_outline_md": "Iterative reversal with `prev` and `next` pointers.",
        "skills": [{"skill_slug": "linked-lists", "weight": 1.0}],
        "hints": [
            "Track three pointers: previous, current, and next.",
            "Point current.next to previous, then advance all pointers.",
        ],
    },
    {
        "slug": "valid-parentheses",
        "title": "Valid Parentheses",
        "topic_slug": "linked-lists-and-stacks",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 20,
        "prompt_md": (
            "Given a string `s` containing `()`, `{}`, and `[]`, determine if the brackets are "
            "valid and properly closed."
        ),
        "solution_outline_md": "Push opening brackets; pop and match on closing brackets.",
        "skills": [{"skill_slug": "stack", "weight": 1.0}],
        "hints": [
            "A closing bracket must match the most recent unmatched opening bracket.",
            "Use a stack to track open brackets.",
        ],
    },
    {
        "slug": "queue-with-stacks",
        "title": "Queue Using Stacks",
        "topic_slug": "linked-lists-and-stacks",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 25,
        "prompt_md": (
            "Implement a FIFO queue using only stack operations (`push`, `pop`, `peek`, "
            "`empty`)."
        ),
        "solution_outline_md": "Two stacks: inbox for enqueue, outbox for dequeue with lazy transfer.",
        "skills": [
            {"skill_slug": "queue", "weight": 1.0},
            {"skill_slug": "stack", "weight": 0.4},
        ],
        "hints": [
            "One stack alone reverses order on pop.",
            "Transfer elements to a second stack only when the output stack is empty.",
        ],
    },
    {
        "slug": "max-tree-depth",
        "title": "Maximum Tree Depth",
        "topic_slug": "trees-and-graphs",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 15,
        "prompt_md": (
            "Given the root of a binary tree, return its maximum depth (number of nodes on the "
            "longest root-to-leaf path)."
        ),
        "solution_outline_md": "Recursive DFS: 1 + max depth of children.",
        "skills": [{"skill_slug": "trees", "weight": 1.0}],
        "hints": [
            "Depth of an empty subtree is 0.",
            "Combine left and right subtree depths with recursion or BFS level counting.",
        ],
    },
    {
        "slug": "count-islands",
        "title": "Count Islands",
        "topic_slug": "trees-and-graphs",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 30,
        "prompt_md": (
            "Given a 2D grid of `1` (land) and `0` (water), count the number of islands. An "
            "island is formed by connecting adjacent lands horizontally or vertically."
        ),
        "solution_outline_md": "DFS or BFS flood fill from each unvisited land cell.",
        "skills": [
            {"skill_slug": "graphs", "weight": 1.0},
            {"skill_slug": "trees", "weight": 0.4},
        ],
        "hints": [
            "Each island is a connected component in the grid graph.",
            "Mark visited cells while exploring to avoid recounting.",
        ],
    },
    {
        "slug": "climbing-stairs",
        "title": "Climbing Stairs",
        "topic_slug": "dynamic-programming",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 20,
        "prompt_md": (
            "You can climb `n` stairs taking 1 or 2 steps at a time. Return how many distinct "
            "ways you can reach the top."
        ),
        "solution_outline_md": "dp[i] = dp[i-1] + dp[i-2] with base cases 1 and 2.",
        "skills": [{"skill_slug": "dynamic-programming", "weight": 1.0}],
        "hints": [
            "The last step is either a 1-step or 2-step move.",
            "This is Fibonacci-style recurrence.",
        ],
    },
    {
        "slug": "house-robber",
        "title": "House Robber",
        "topic_slug": "dynamic-programming",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 30,
        "prompt_md": (
            "Given `nums` representing money in each house, return the maximum you can rob "
            "without robbing two adjacent houses."
        ),
        "solution_outline_md": "dp[i] = max(dp[i-1], dp[i-2] + nums[i]).",
        "skills": [{"skill_slug": "dynamic-programming", "weight": 1.0}],
        "hints": [
            "At each house choose to rob it (skip previous) or skip it (keep previous best).",
            "Only two prior states are needed for the recurrence.",
        ],
    },
    {
        "slug": "coin-change-min",
        "title": "Coin Change Minimum",
        "topic_slug": "dynamic-programming",
        "difficulty": Difficulty.MEDIUM,
        "estimated_minutes": 35,
        "prompt_md": (
            "Given coin denominations `coins` and amount `amount`, return the fewest coins needed "
            "to make `amount`, or -1 if impossible."
        ),
        "solution_outline_md": "Bottom-up DP: dp[a] = min coins for amount a.",
        "skills": [{"skill_slug": "dynamic-programming", "weight": 1.0}],
        "hints": [
            "Try every coin for each sub-amount from 1 to `amount`.",
            "Initialize dp with a large sentinel except dp[0] = 0.",
        ],
    },
]
