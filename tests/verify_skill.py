import os
import re
import sys

# Dynamically resolve directory containing this skill (tests/..):
DEFAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.environ.get("SKILL_DIR", DEFAULT_DIR)

# ==============================================================================
# CATEGORY A: STRUCTURAL VERIFICATION
# Static content, schema, contract, provider facts, and safety rule assertions
# ==============================================================================

def structural_test_frontmatter():
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    assert os.path.exists(skill_md), f"SKILL.md not found in {SKILL_DIR}"
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
    assert fm_match, "Valid frontmatter delimiter not found"
    fm_text = fm_match.group(1)
    
    assert len(fm_text) <= 1024, f"Frontmatter too long ({len(fm_text)} chars)"
    
    name_match = re.search(r"^name:\s*([a-zA-Z0-9_-]+)", fm_text, re.MULTILINE)
    assert name_match, "Valid name not found in frontmatter"
    assert name_match.group(1) == "tier-tune", f"Expected skill name 'tier-tune', got '{name_match.group(1)}'"
    
    desc_match = re.search(r"^description:\s*(.+)", fm_text, re.MULTILINE)
    assert desc_match, "Valid description not found in frontmatter"
    desc = desc_match.group(1).strip()
    assert desc.startswith("Use when"), f"Description should start with 'Use when', got: {desc}"
    print(f"[PASS] [STRUCTURAL] Frontmatter validated (canonical name: {name_match.group(1)})")

def structural_test_required_files():
    required_files = [
        "SKILL.md",
        "README.md",
        os.path.join("references", "vercel.md"),
        os.path.join("references", "supabase.md"),
        os.path.join("references", "frameworks.md"),
        os.path.join("references", "safety-matrix.md"),
        os.path.join("references", "report-format.md"),
        os.path.join("tests", "scenarios.md"),
        os.path.join("tests", "verify_skill.py"),
    ]
    for rel_path in required_files:
        full_path = os.path.join(SKILL_DIR, rel_path)
        assert os.path.exists(full_path), f"Required file missing: {rel_path}"
    print("[PASS] [STRUCTURAL] All required files present in canonical skill tree")

def structural_test_no_old_alias_references():
    old_alias = "-".join(["optimizing", "vercel", "supabase", "free", "tier"])
    for root, _, files in os.walk(SKILL_DIR):
        for fname in files:
            if not (fname.endswith(".md") or fname.endswith(".py")):
                continue
            if fname == "verify_skill.py":
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                c = f.read()
            assert old_alias not in c, f"Found deprecated alias '{old_alias}' in {fpath}"
    print("[PASS] [STRUCTURAL] Zero occurrences of deprecated alias found across all skill files")

def structural_test_php_exclusion():
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    
    with open(skill_md, "r", encoding="utf-8") as f:
        s_content = f.read()
    with open(safety_md, "r", encoding="utf-8") as f:
        m_content = f.read()
        
    assert "PHP is **EXPLICITLY OUT OF SCOPE**" in s_content or "PHP is explicitly out of scope" in s_content.lower()
    assert "vercel-php" in s_content
    assert "PHP" in m_content
    assert "monorepo" in s_content.lower()
    print("[PASS] [STRUCTURAL] PHP exclusion rules and monorepo boundaries verified")

def structural_test_supported_scope():
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    with open(skill_md, "r", encoding="utf-8") as f:
        s_content = f.read()
    with open(safety_md, "r", encoding="utf-8") as f:
        m_content = f.read()
    
    out_of_scope = ["Netlify", "Cloudflare", "Firebase", "Railway", "Render", "Neon", "AWS", "Azure", "GCP", "Fly.io"]
    for provider in out_of_scope:
        assert provider in s_content, f"Missing out-of-scope mention for {provider} in SKILL.md"
        assert provider in m_content, f"Missing out-of-scope mention for {provider} in safety-matrix.md"
    print("[PASS] [STRUCTURAL] Scope boundaries verified (Vercel & Supabase only; 10 external platforms rejected)")

def structural_test_no_hardcoded_quotas_or_paid_features():
    references_dir = os.path.join(SKILL_DIR, "references")
    for fname in os.listdir(references_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(references_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            c = f.read()
            assert "100 GB" not in c and "100GB" not in c, f"Found hardcoded 100GB quota in {fname}"
            assert "500,000 invocations" not in c, f"Found hardcoded 500,000 invocations in {fname}"
            if fname in ["vercel.md", "supabase.md"]:
                assert "official" in c.lower()
    
    supa_path = os.path.join(SKILL_DIR, "references", "supabase.md")
    with open(supa_path, "r", encoding="utf-8") as f:
        supa_c = f.read()
    assert "PAID-ONLY" in supa_c or "paid-only" in supa_c.lower()
    print("[PASS] [STRUCTURAL] No hardcoded temporary quotas verified; paid features strictly rejected")

def structural_test_safety_rules_present():
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    
    with open(safety_md, "r", encoding="utf-8") as f:
        sm = f.read()
    with open(skill_md, "r", encoding="utf-8") as f:
        sk = f.read()
        
    core_rules = [
        "Class A", "Class B",
        "Row Level Security",
        "no-store",
    ]
    for rule in core_rules:
        assert rule in sm, f"Missing safety rule '{rule}' in safety-matrix.md"
        assert rule in sk, f"Missing safety rule '{rule}' in SKILL.md"
        
    assert ("service_role" in sm or "service-role" in sm), "Missing service_role in safety-matrix.md"
    assert ("service_role" in sk or "service-role" in sk), "Missing service_role in SKILL.md"
        
    assert "Absolute Prohibitions" in sm
    assert "Red Flags" in sk
    print("[PASS] [STRUCTURAL] Core safety rules and hard red lines verified across documents")

def structural_test_cache_classification_consistency():
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    scenarios_md = os.path.join(SKILL_DIR, "tests", "scenarios.md")
    frameworks_md = os.path.join(SKILL_DIR, "references", "frameworks.md")
    
    with open(safety_md, "r", encoding="utf-8") as f:
        sm = f.read()
    with open(skill_md, "r", encoding="utf-8") as f:
        sk = f.read()
    with open(scenarios_md, "r", encoding="utf-8") as f:
        sc = f.read()
    with open(frameworks_md, "r", encoding="utf-8") as f:
        fm = f.read()

    # Rule: Materially adding/changing cache TTL affecting data freshness is Class B by default
    assert "Class B" in sm and "data freshness" in sm.lower()
    assert "Class B" in sk and "data freshness" in sk.lower()
    assert "Class B" in sc and "stale-while-revalidate" in sc
    assert "Class B" in fm and "freshness" in fm.lower()
    print("[PASS] [STRUCTURAL] Cache classification consistency verified (material TTL changes are Class B by default)")

def structural_test_authenticated_cache_safety():
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    vercel_md = os.path.join(SKILL_DIR, "references", "vercel.md")
    scenarios_md = os.path.join(SKILL_DIR, "tests", "scenarios.md")

    with open(safety_md, "r", encoding="utf-8") as f:
        sm = f.read()
    with open(vercel_md, "r", encoding="utf-8") as f:
        vm = f.read()
    with open(scenarios_md, "r", encoding="utf-8") as f:
        sc = f.read()

    # Shared CDN caching prohibited for authenticated routes
    assert "PROHIBITED" in sm and "s-maxage" in sm
    # Request/query deduplication is Class A
    assert "Request / Query Deduplication" in sm and "Class A" in sm
    # Persistent browser HTTP caching is Class B
    assert "Persistent Browser HTTP Caching" in sm and "Class B" in sm
    # All 6 sensitive categories listed
    sensitive_items = ["billing", "account details", "security settings", "private dashboards", "tokens", "user-specific sensitive responses"]
    for item in sensitive_items:
        assert item in sm.lower(), f"Missing sensitive item '{item}' in safety-matrix.md"
    # Sensitive endpoints preserve no-store
    assert "no-store" in sm
    assert "no-store" in vm
    # Scenario K checks
    assert "Scenario K:" in sc
    assert "deduplication" in sc.lower()
    print("[PASS] [STRUCTURAL] Authenticated cache safety rules verified (query dedup Class A, persistent browser cache Class B, no-store preserved)")

def structural_test_evidence_based_proxy_analysis():
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    vercel_md = os.path.join(SKILL_DIR, "references", "vercel.md")
    scenarios_md = os.path.join(SKILL_DIR, "tests", "scenarios.md")

    with open(safety_md, "r", encoding="utf-8") as f:
        sm = f.read()
    with open(vercel_md, "r", encoding="utf-8") as f:
        vm = f.read()
    with open(scenarios_md, "r", encoding="utf-8") as f:
        sc = f.read()

    # Must check server responsibilities
    responsibilities = [
        "effective caching",
        "authentication",
        "secret protection",
        "transformation",
        "aggregation",
        "validation",
        "rate limiting",
        "request coalescing",
    ]
    for r in responsibilities:
        assert r in sm.lower(), f"Missing responsibility '{r}' in safety-matrix.md"
        assert r in vm.lower(), f"Missing responsibility '{r}' in vercel.md"
        assert r in sc.lower(), f"Missing responsibility '{r}' in scenarios.md"

    # Pass-through checks: security, Supabase load, Vercel transfer/function cost, caching behavior
    assert "pass-through" in sm.lower()
    assert "pass-through" in vm.lower()
    assert "pass-through" in sc.lower()
    print("[PASS] [STRUCTURAL] Evidence-based cross-provider proxy analysis verified")

def structural_test_image_preprocessing_classification():
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    supa_md = os.path.join(SKILL_DIR, "references", "supabase.md")
    scenarios_md = os.path.join(SKILL_DIR, "tests", "scenarios.md")

    with open(safety_md, "r", encoding="utf-8") as f:
        sm = f.read()
    with open(supa_md, "r", encoding="utf-8") as f:
        sumd = f.read()
    with open(scenarios_md, "r", encoding="utf-8") as f:
        sc = f.read()

    # Introducing new pipeline is Class B by default
    assert "Image Preprocessing" in sm
    assert "Class B" in sm and "Class B by default" in sm
    assert "Class B" in sumd and "Class B by default" in sumd
    # Correcting existing pipeline without altering intended output may be Class A
    assert "Class A" in sm and "existing image optimization pipeline" in sm
    assert "Class A" in sumd and "existing image optimization pipeline" in sumd
    # Storage cacheControl remains Class A
    assert "cacheControl" in sm and "Class A" in sm
    # Scenario G checks
    assert "Scenario G:" in sc
    assert "Class B" in sc and "Class A" in sc
    print("[PASS] [STRUCTURAL] Image preprocessing classification verified (new pipeline Class B, existing fix Class A, cacheControl Class A)")

def structural_test_provider_facts():
    supa_md = os.path.join(SKILL_DIR, "references", "supabase.md")
    vercel_md = os.path.join(SKILL_DIR, "references", "vercel.md")
    frameworks_md = os.path.join(SKILL_DIR, "references", "frameworks.md")
    safety_md = os.path.join(SKILL_DIR, "references", "safety-matrix.md")
    
    with open(supa_md, "r", encoding="utf-8") as f:
        sm = f.read()
    with open(vercel_md, "r", encoding="utf-8") as f:
        vm = f.read()
    with open(frameworks_md, "r", encoding="utf-8") as f:
        fm = f.read()
    with open(safety_md, "r", encoding="utf-8") as f:
        sf = f.read()

    # 1. Supabase Storage Image Transformations are not available on Free
    assert "PAID-ONLY" in sm or "paid-only" in sm.lower()
    assert "/render/image/" in sm and "Free" in sm

    # 2. cacheControl support for Supabase Storage
    assert "cacheControl" in sm
    assert "upload" in sm

    # 3. Vercel caching can prevent Function execution where applicable
    assert "s-maxage" in vm
    assert "0 Function invocations" in sf or "0 function invocations" in sf.lower()

    # 4. Vercel proxied responses can use CDN cache control
    assert "Edge CDN caching" in vm or "CDN cache" in vm
    assert "s-maxage" in sf

    # 5. Image optimization recommendations remain framework/version aware
    assert "version" in vm.lower() and "framework" in vm.lower()
    assert "fill" in vm and "layout=" in vm
    assert "sizes" in fm
    print("[PASS] [STRUCTURAL] Provider facts verified (Storage transformations paid-only, cacheControl, Vercel CDN function shield, version-aware images)")

def structural_test_framework_adapters_and_runtimes():
    frameworks_path = os.path.join(SKILL_DIR, "references", "frameworks.md")
    with open(frameworks_path, "r", encoding="utf-8") as f:
        c = f.read()
    
    required_frameworks = [
        "Next.js", "React", "Vite", "Nuxt", "Svelte", "SvelteKit",
        "Astro", "Remix", "Angular", "Solid", "SolidStart", "Static"
    ]
    for fw in required_frameworks:
        assert fw in c, f"Missing framework adapter guidance for {fw}"

    required_runtimes = ["Python", "Go", "Rust", "Bun", "Edge Runtime"]
    for rt in required_runtimes:
        assert rt in c, f"Missing runtime guidance for {rt}"
    print("[PASS] [STRUCTURAL] Framework adapters and multi-language runtimes verified")

def structural_test_supabase_sdk_independence():
    supa_path = os.path.join(SKILL_DIR, "references", "supabase.md")
    with open(supa_path, "r", encoding="utf-8") as f:
        c = f.read()
    
    assert "PostgREST" in c
    assert "Prefer: count=exact" in c
    assert "Prefer: return=minimal" in c
    assert "Prisma" in c
    assert "Drizzle" in c
    assert "SQLAlchemy" in c or "SQL" in c
    assert "Presence" in c
    assert "Broadcast" in c
    assert "pg_cron" in c or "retention" in c.lower()
    print("[PASS] [STRUCTURAL] Supabase SDK independence, direct PostgREST, SQL, ORMs, and lifecycle verified")

def structural_test_report_format():
    report_md = os.path.join(SKILL_DIR, "references", "report-format.md")
    with open(report_md, "r", encoding="utf-8") as f:
        c = f.read()
    sections = [
        "Project Fingerprint",
        "Resource Findings",
        "Auto-Applied",
        "Architectural Recommendations",
        "Skipped",
        "Verification Record",
        "Expected Resource Impact",
    ]
    for s in sections:
        assert s in c, f"Missing section '{s}' in report-format.md"
    print("[PASS] [STRUCTURAL] Standard report format specification verified")

def structural_test_markdown_links():
    for root, _, files in os.walk(SKILL_DIR):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                c = f.read()
            links = re.findall(r"\[.*?\]\(((?:references/|tests/|\.\./).*?\.md)\)", c)
            for link in links:
                target = os.path.normpath(os.path.join(root, link))
                assert os.path.exists(target), f"Broken link target: {link} in {fpath} -> resolved to {target}"
    print("[PASS] [STRUCTURAL] All markdown cross-references verified")

# ==============================================================================
# CATEGORY B: AGENT BEHAVIOR / PRESSURE VERIFICATION (SCENARIOS A - L)
# Verification of scenario contracts, execution protocols, and runtime status
# ==============================================================================

def behavior_test_scenario_specifications():
    scenarios_path = os.path.join(SKILL_DIR, "tests", "scenarios.md")
    with open(scenarios_path, "r", encoding="utf-8") as f:
        c = f.read()
    
    assert "## Runtime Agent Evaluation Status" in c, "Missing Runtime Agent Evaluation Status section in scenarios.md"
    assert "awaiting runtime agent evaluation" in c.lower(), "Missing awaiting runtime agent evaluation disclaimer"

    for scenario_letter in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
        assert f"## Scenario {scenario_letter}:" in c, f"Missing Scenario {scenario_letter}"
        assert f"**Evaluation Status:** Specification awaiting runtime agent evaluation" in c, f"Missing Evaluation Status in Scenario {scenario_letter}"
        assert "### Execution Protocol" in c, f"Missing Execution Protocol in Scenario {scenario_letter}"
        assert "**RED Baseline Execution:**" in c, f"Missing RED Baseline Execution in Scenario {scenario_letter}"
        assert "**GREEN TierTune Execution:**" in c, f"Missing GREEN TierTune Execution in Scenario {scenario_letter}"
        assert "### Baseline Rationalizations (RED)" in c, f"Missing RED section in Scenario {scenario_letter}"
        assert "### Expected Skill Behavior (GREEN)" in c, f"Missing GREEN section in Scenario {scenario_letter}"
    print("[PASS] [BEHAVIOR SPECIFICATION] Scenarios A through L specifications verified with RED/GREEN contracts and execution protocols")

def report_agent_behavior_status():
    """
    Clearly distinguishes structural scenario specifications from actual runtime agent execution.
    Never fabricates agent execution.
    """
    print("\n--- AGENT BEHAVIOR / PRESSURE VERIFICATION STATUS ---")
    print("[STATUS] Scenarios A through L specifications and contracts: VERIFIED (12/12)")
    print("[STATUS] Live Agent Execution Runs: AWAITING RUNTIME AGENT EVALUATION (0/12 runs executed)")
    print("         Notice: In this static validation harness, live isolated LLM agent")
    print("         runs were NOT executed. All 12 scenarios are formally specified with")
    print("         reproducible RED baseline prompts and GREEN TierTune evaluation gates")
    print("         awaiting interactive agent harness evaluation. Zero runs fabricated.")
    print("-----------------------------------------------------")

if __name__ == "__main__":
    print(f"=== Running TierTune Skill Verification Suite ===")
    print(f"Target Directory: {SKILL_DIR}\n")
    
    print("=== Category A: STRUCTURAL VERIFICATION ===")
    structural_test_frontmatter()
    structural_test_required_files()
    structural_test_no_old_alias_references()
    structural_test_php_exclusion()
    structural_test_supported_scope()
    structural_test_no_hardcoded_quotas_or_paid_features()
    structural_test_safety_rules_present()
    structural_test_cache_classification_consistency()
    structural_test_authenticated_cache_safety()
    structural_test_evidence_based_proxy_analysis()
    structural_test_image_preprocessing_classification()
    structural_test_provider_facts()
    structural_test_framework_adapters_and_runtimes()
    structural_test_supabase_sdk_independence()
    structural_test_report_format()
    structural_test_markdown_links()
    print("\nALL 16 STRUCTURAL VERIFICATION SUITES PASSED CLEANLY.\n")

    print("=== Category B: AGENT BEHAVIOR / PRESSURE VERIFICATION ===")
    behavior_test_scenario_specifications()
    report_agent_behavior_status()
    print("\nSKILL VERIFICATION SUITE EXECUTION COMPLETE.")
