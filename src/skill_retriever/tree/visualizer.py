"""
Tree Visualizer - Generate interactive HTML visualization of the skill tree.
"""

import json
from pathlib import Path


def generate_html(tree_dict: dict, output_path: Path) -> None:
    """
    Generate an interactive HTML visualization of the skill tree.

    Args:
        tree_dict: Tree data in dict format (domains -> types -> skills)
        output_path: Path to write the HTML file
    """
    # Convert tree to D3.js compatible format
    d3_data = _convert_to_d3_format(tree_dict)

    # Calculate statistics
    stats = _calculate_stats(tree_dict)

    # Generate HTML
    html_content = _generate_html_template(d3_data, stats)

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def _convert_to_d3_format(tree_dict: dict) -> dict:
    """Convert tree dict to D3.js hierarchical format."""
    # Support both new recursive format and legacy format
    if "children" in tree_dict:
        return _convert_recursive_format(tree_dict)
    else:
        return _convert_legacy_format(tree_dict)


def _convert_recursive_format(node_dict: dict, depth: int = 0) -> dict:
    """Convert new recursive format to D3.js format."""
    has_children = bool(node_dict.get("children"))
    has_skills = bool(node_dict.get("skills"))

    # Determine node type based on structure
    if depth == 0:
        node_type = "root"
    elif has_children:
        node_type = "category"
    elif has_skills:
        node_type = "type"
    else:
        node_type = "skill"

    result = {
        "name": node_dict.get("name", node_dict.get("id", "Unknown")),
        "id": node_dict.get("id", ""),
        "description": node_dict.get("description", ""),
        "type": node_type,
        "children": []
    }

    # Recursively process children
    for child in node_dict.get("children", []):
        result["children"].append(_convert_recursive_format(child, depth + 1))

    # Process skills (leaf nodes)
    for skill in node_dict.get("skills", []):
        result["children"].append({
            "name": skill.get("name", skill.get("id", "")),
            "id": skill.get("id", ""),
            "description": skill.get("description", ""),
            "type": "skill"
        })

    return result


def _convert_legacy_format(tree_dict: dict) -> dict:
    """Convert legacy domains/types format to D3.js format."""
    root = {
        "name": "Skills",
        "children": []
    }

    for domain_id, domain_data in tree_dict.get("domains", {}).items():
        domain_node = {
            "name": domain_data.get("name", domain_id),
            "id": domain_id,
            "description": domain_data.get("description", ""),
            "type": "domain",
            "children": []
        }

        for type_id, type_data in domain_data.get("types", {}).items():
            type_node = {
                "name": type_data.get("name", type_id),
                "id": type_id,
                "description": type_data.get("description", ""),
                "type": "type",
                "children": []
            }

            for skill in type_data.get("skills", []):
                skill_node = {
                    "name": skill.get("name", skill.get("id", "")),
                    "id": skill.get("id", ""),
                    "description": skill.get("description", ""),
                    "type": "skill"
                }
                type_node["children"].append(skill_node)

            domain_node["children"].append(type_node)

        root["children"].append(domain_node)

    return root


def _calculate_stats(tree_dict: dict) -> dict:
    """Calculate tree statistics."""
    # Support both new recursive format and legacy format
    if "children" in tree_dict:
        return _calculate_stats_recursive(tree_dict)
    else:
        return _calculate_stats_legacy(tree_dict)


def _calculate_stats_recursive(node_dict: dict) -> dict:
    """Calculate stats for new recursive format."""
    categories = 0
    skills = 0
    max_depth = 0

    def count_node(node, depth):
        nonlocal categories, skills, max_depth
        max_depth = max(max_depth, depth)

        # A category is any node that has children OR skills (i.e., not a skill itself)
        has_children = bool(node.get("children"))
        has_skills = bool(node.get("skills"))

        if has_children or has_skills:
            categories += 1

        if has_children:
            for child in node["children"]:
                count_node(child, depth + 1)

        if has_skills:
            skills += len(node["skills"])

    for child in node_dict.get("children", []):
        count_node(child, 1)

    skills += len(node_dict.get("skills", []))

    return {
        "categories": categories,
        "skills": skills,
        "depth": max_depth
    }


def _calculate_stats_legacy(tree_dict: dict) -> dict:
    """Calculate stats for legacy domains/types format."""
    domains = tree_dict.get("domains", {})
    total_types = 0
    total_skills = 0

    for domain_data in domains.values():
        types = domain_data.get("types", {})
        total_types += len(types)
        for type_data in types.values():
            total_skills += len(type_data.get("skills", []))

    return {
        "categories": len(domains) + total_types,
        "skills": total_skills,
        "depth": 2  # Fixed depth for legacy format
    }


def _generate_html_template(d3_data: dict, stats: dict) -> str:
    """Generate the HTML template with embedded data."""
    tree_json = json.dumps(d3_data, ensure_ascii=False, indent=2)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skill Tree Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e4;
            min-height: 100vh;
            overflow-x: hidden;
        }}

        .header {{
            padding: 20px 40px;
            background: rgba(0, 0, 0, 0.3);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .header h1 {{
            font-size: 24px;
            font-weight: 600;
            color: #fff;
        }}

        .stats {{
            display: flex;
            gap: 30px;
            padding: 20px 40px;
            background: rgba(0, 0, 0, 0.2);
        }}

        .stat-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #4fc3f7;
        }}

        .stat-label {{
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
        }}

        .search-container {{
            padding: 15px 40px;
            background: rgba(0, 0, 0, 0.1);
            position: relative;
        }}

        .search-wrapper {{
            position: relative;
            max-width: 500px;
        }}

        .search-input {{
            width: 100%;
            padding: 12px 40px 12px 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            font-size: 14px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .search-input::placeholder {{
            color: #666;
        }}

        .search-input:focus {{
            outline: none;
            border-color: #4fc3f7;
            box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.2);
        }}

        .search-clear {{
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            width: 20px;
            height: 20px;
            border: none;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            color: #fff;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            line-height: 1;
        }}

        .search-clear:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        .search-clear.visible {{
            display: flex;
        }}

        .search-info {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-top: 10px;
        }}

        .search-count {{
            font-size: 13px;
            color: #4fc3f7;
            display: none;
        }}

        .search-count.visible {{
            display: block;
        }}

        .search-nav {{
            display: none;
            gap: 5px;
        }}

        .search-nav.visible {{
            display: flex;
        }}

        .search-nav button {{
            padding: 4px 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            cursor: pointer;
            font-size: 12px;
        }}

        .search-nav button:hover {{
            background: rgba(79, 195, 247, 0.2);
            border-color: #4fc3f7;
        }}

        .search-nav button:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}

        .search-results {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            max-width: 500px;
            max-height: 300px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-top: none;
            border-radius: 0 0 8px 8px;
            display: none;
            z-index: 100;
        }}

        .search-results.visible {{
            display: block;
        }}

        .search-result-item {{
            padding: 10px 15px;
            cursor: pointer;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            transition: background 0.15s;
        }}

        .search-result-item:last-child {{
            border-bottom: none;
        }}

        .search-result-item:hover,
        .search-result-item.active {{
            background: rgba(79, 195, 247, 0.2);
        }}

        .search-result-name {{
            font-weight: 500;
            color: #fff;
            margin-bottom: 2px;
        }}

        .search-result-path {{
            font-size: 11px;
            color: #888;
        }}

        .search-result-type {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            margin-left: 8px;
            text-transform: uppercase;
        }}

        .search-result-type--skill {{
            background: rgba(255, 183, 77, 0.3);
            color: #ffb74d;
        }}

        .search-result-type--category {{
            background: rgba(79, 195, 247, 0.3);
            color: #4fc3f7;
        }}

        .tree-container {{
            padding: 20px;
            overflow: auto;
        }}

        .node circle {{
            cursor: pointer;
            stroke-width: 2px;
            transition: stroke-width 0.2s, filter 0.2s;
        }}

        .node text {{
            font-size: 12px;
            fill: #e4e4e4;
            transition: font-weight 0.2s;
        }}

        .node--domain circle,
        .node--category circle {{
            fill: #4fc3f7;
            stroke: #4fc3f7;
        }}

        .node--type circle {{
            fill: #81c784;
            stroke: #81c784;
        }}

        .node--skill circle {{
            fill: #ffb74d;
            stroke: #ffb74d;
        }}

        .node--category circle {{
            fill: #4fc3f7;
            stroke: #4fc3f7;
        }}

        .node--collapsed circle {{
            fill: #1a1a2e;
        }}

        .node--match circle {{
            stroke: #ffd700 !important;
            stroke-width: 4px !important;
            filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.8));
        }}

        .node--match text {{
            font-weight: 700;
            fill: #ffd700;
        }}

        .node--current circle {{
            stroke: #ff4081 !important;
            stroke-width: 5px !important;
            filter: drop-shadow(0 0 12px rgba(255, 64, 129, 0.9));
        }}

        .node--current text {{
            font-weight: 700;
            fill: #ff4081;
        }}

        .link {{
            fill: none;
            stroke: rgba(255, 255, 255, 0.2);
            stroke-width: 1.5px;
        }}

        .tooltip {{
            position: absolute;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            font-size: 13px;
            max-width: 300px;
            pointer-events: none;
            z-index: 1000;
        }}

        .tooltip-title {{
            font-weight: 600;
            margin-bottom: 5px;
            color: #4fc3f7;
        }}

        .tooltip-desc {{
            color: #aaa;
            line-height: 1.4;
        }}

        .legend {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 8px;
            font-size: 12px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 5px;
        }}

        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}

        .legend-dot--domain {{ background: #4fc3f7; }}
        .legend-dot--type {{ background: #81c784; }}
        .legend-dot--skill {{ background: #ffb74d; }}

        .highlight {{
            font-weight: bold;
        }}

        .dimmed {{
            opacity: 0.3;
        }}

        .keyboard-hint {{
            font-size: 11px;
            color: #666;
            margin-left: auto;
        }}

        .keyboard-hint kbd {{
            display: inline-block;
            padding: 2px 5px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            font-family: inherit;
            margin: 0 2px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Skill Tree Visualization</h1>
    </div>

    <div class="stats">
        <div class="stat-item">
            <span class="stat-value">{stats['skills']}</span>
            <span class="stat-label">Skills</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">{stats['categories']}</span>
            <span class="stat-label">Categories</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">{stats['depth']}</span>
            <span class="stat-label">Max Depth</span>
        </div>
    </div>

    <div class="search-container">
        <div class="search-wrapper">
            <input type="text" class="search-input" placeholder="Search skills by name, id, or description..." id="search" autocomplete="off">
            <button class="search-clear" id="search-clear" title="Clear search">&times;</button>
            <div class="search-results" id="search-results"></div>
        </div>
        <div class="search-info">
            <span class="search-count" id="search-count"></span>
            <div class="search-nav" id="search-nav">
                <button id="prev-result" title="Previous result (↑)">&#9650; Prev</button>
                <button id="next-result" title="Next result (↓)">Next &#9660;</button>
            </div>
            <span class="keyboard-hint"><kbd>↑</kbd><kbd>↓</kbd> navigate <kbd>Enter</kbd> jump <kbd>Esc</kbd> close</span>
        </div>
    </div>

    <div class="tree-container" id="tree"></div>

    <div class="legend">
        <div class="legend-item">
            <span class="legend-dot legend-dot--domain"></span>
            <span>Category</span>
        </div>
        <div class="legend-item">
            <span class="legend-dot legend-dot--skill"></span>
            <span>Skill</span>
        </div>
    </div>

    <div class="tooltip" id="tooltip" style="display: none;"></div>

    <script>
        const treeData = {tree_json};

        const marginLeft = 60;
        const marginTop = 50;
        const nodeVerticalSpacing = 30;  // Vertical spacing between nodes
        const nodeHorizontalSpacing = 220;  // Horizontal spacing between depth levels

        const root = d3.hierarchy(treeData);
        root.x0 = 0;
        root.y0 = 0;

        // Collapse children initially for domains
        root.children.forEach(d => {{
            if (d.children) {{
                d._children = d.children;
                d.children = null;
            }}
        }});

        const svgElement = d3.select("#tree")
            .append("svg")
            .attr("width", window.innerWidth)
            .attr("height", Math.max(window.innerHeight - 200, 800));

        const svg = svgElement.append("g")
            .attr("transform", `translate(${{marginLeft}}, ${{marginTop}})`);

        // Use nodeSize for consistent spacing instead of fixed size
        const tree = d3.tree()
            .nodeSize([nodeVerticalSpacing, nodeHorizontalSpacing])
            .separation((a, b) => a.parent === b.parent ? 1 : 1.5);

        const tooltip = d3.select("#tooltip");

        // Search state
        let searchMatches = [];
        let currentMatchIndex = -1;

        function update(source) {{
            const duration = 300;

            // Compute the new tree layout
            tree(root);

            const nodes = root.descendants();
            const links = root.links();

            // Calculate bounds of visible nodes
            let minX = Infinity, maxX = -Infinity;
            let maxY = 0;
            nodes.forEach(d => {{
                minX = Math.min(minX, d.x);
                maxX = Math.max(maxX, d.x);
                maxY = Math.max(maxY, d.y);
            }});

            // Dynamic SVG sizing based on tree bounds
            const treeHeight = maxX - minX + 100;
            const treeWidth = maxY + 300;
            const newHeight = Math.max(treeHeight, window.innerHeight - 200, 800);
            const newWidth = Math.max(treeWidth, window.innerWidth);

            svgElement
                .transition()
                .duration(duration)
                .attr("height", newHeight)
                .attr("width", newWidth);

            // Adjust g transform to center tree vertically (offset by minX)
            svg.transition()
                .duration(duration)
                .attr("transform", `translate(${{marginLeft}}, ${{-minX + marginTop}})`);

            // Nodes
            const node = svg.selectAll("g.node")
                .data(nodes, d => d.data.id || d.data.name);

            const nodeEnter = node.enter()
                .append("g")
                .attr("class", d => `node node--${{d.data.type || 'root'}}`)
                .attr("transform", d => `translate(${{source.y0}}, ${{source.x0}})`)
                .on("click", (event, d) => {{
                    if (d.children) {{
                        d._children = d.children;
                        d.children = null;
                    }} else if (d._children) {{
                        d.children = d._children;
                        d._children = null;
                        // Collapse grandchildren to expand one level at a time
                        d.children.forEach(child => {{
                            if (child.children) {{
                                child._children = child.children;
                                child.children = null;
                            }}
                        }});
                    }}
                    update(d);
                }})
                .on("mouseover", (event, d) => {{
                    if (d.data.description) {{
                        tooltip.style("display", "block")
                            .html(`<div class="tooltip-title">${{d.data.name}}</div><div class="tooltip-desc">${{d.data.description}}</div>`)
                            .style("left", (event.pageX + 10) + "px")
                            .style("top", (event.pageY - 10) + "px");
                    }}
                }})
                .on("mouseout", () => {{
                    tooltip.style("display", "none");
                }});

            nodeEnter.append("circle")
                .attr("r", d => d.data.type === 'skill' ? 5 : 8)
                .attr("class", d => d._children ? "node--collapsed" : "");

            nodeEnter.append("text")
                .attr("dy", "0.35em")
                .attr("x", d => d.children || d._children ? -12 : 12)
                .attr("text-anchor", d => d.children || d._children ? "end" : "start")
                .text(d => d.data.name);

            const nodeUpdate = nodeEnter.merge(node);

            nodeUpdate.transition()
                .duration(duration)
                .attr("transform", d => `translate(${{d.y}}, ${{d.x}})`);

            nodeUpdate.select("circle")
                .attr("class", d => d._children ? "node--collapsed" : "");

            const nodeExit = node.exit()
                .transition()
                .duration(duration)
                .attr("transform", d => `translate(${{source.y}}, ${{source.x}})`)
                .remove();

            // Links
            const link = svg.selectAll("path.link")
                .data(links, d => d.target.data.id || d.target.data.name);

            const linkEnter = link.enter()
                .insert("path", "g")
                .attr("class", "link")
                .attr("d", d => {{
                    const o = {{x: source.x0, y: source.y0}};
                    return diagonal(o, o);
                }});

            linkEnter.merge(link)
                .transition()
                .duration(duration)
                .attr("d", d => diagonal(d.source, d.target));

            link.exit()
                .transition()
                .duration(duration)
                .attr("d", d => {{
                    const o = {{x: source.x, y: source.y}};
                    return diagonal(o, o);
                }})
                .remove();

            nodes.forEach(d => {{
                d.x0 = d.x;
                d.y0 = d.y;
            }});

            // Update search highlights after tree update
            updateSearchHighlights();
        }}

        function diagonal(s, d) {{
            return `M ${{s.y}} ${{s.x}}
                    C ${{(s.y + d.y) / 2}} ${{s.x}},
                      ${{(s.y + d.y) / 2}} ${{d.x}},
                      ${{d.y}} ${{d.x}}`;
        }}

        update(root);

        // === Enhanced Search Functionality ===

        function getAllNodes(node) {{
            // Recursively get all nodes including collapsed ones
            const nodes = [node];
            const children = node.children || node._children || [];
            children.forEach(child => {{
                nodes.push(...getAllNodes(child));
            }});
            return nodes;
        }}

        function searchTree(query) {{
            if (!query) return [];

            const allNodes = getAllNodes(root);
            const matches = [];

            allNodes.forEach(node => {{
                const name = (node.data.name || "").toLowerCase();
                const id = (node.data.id || "").toLowerCase();
                const desc = (node.data.description || "").toLowerCase();

                if (name.includes(query) || id.includes(query) || desc.includes(query)) {{
                    matches.push(node);
                }}
            }});

            return matches;
        }}

        function getNodePath(node) {{
            const path = [];
            let current = node;
            while (current.parent) {{
                path.unshift(current.data.name);
                current = current.parent;
            }}
            return path.join(" > ");
        }}

        function expandToNode(node) {{
            // Expand all ancestors to make the node visible
            const ancestors = node.ancestors().reverse();
            ancestors.forEach(ancestor => {{
                if (ancestor._children) {{
                    ancestor.children = ancestor._children;
                    ancestor._children = null;
                }}
            }});
        }}

        function scrollToNode(node) {{
            // Wait for D3 transition to complete then scroll
            setTimeout(() => {{
                const nodeElement = svg.selectAll("g.node")
                    .filter(d => d === node)
                    .node();

                if (nodeElement) {{
                    const rect = nodeElement.getBoundingClientRect();
                    const container = document.querySelector('.tree-container');
                    const containerRect = container.getBoundingClientRect();

                    // Calculate scroll position to center the node
                    const scrollLeft = rect.left - containerRect.left + container.scrollLeft - containerRect.width / 2;
                    const scrollTop = rect.top - containerRect.top + container.scrollTop - containerRect.height / 2;

                    container.scrollTo({{
                        left: Math.max(0, scrollLeft),
                        top: Math.max(0, scrollTop),
                        behavior: 'smooth'
                    }});
                }}
            }}, 350);
        }}

        function updateSearchHighlights() {{
            // Clear all highlights
            svg.selectAll("g.node")
                .classed("node--match", false)
                .classed("node--current", false);

            if (searchMatches.length === 0) return;

            // Get node IDs for matching
            const matchIds = new Set(searchMatches.map(n => n.data.id || n.data.name));

            // Highlight all matches
            svg.selectAll("g.node")
                .classed("node--match", d => matchIds.has(d.data.id || d.data.name));

            // Highlight current match
            if (currentMatchIndex >= 0 && currentMatchIndex < searchMatches.length) {{
                const currentNode = searchMatches[currentMatchIndex];
                svg.selectAll("g.node")
                    .filter(d => d === currentNode)
                    .classed("node--current", true);
            }}
        }}

        function renderSearchResults(matches, query) {{
            const resultsEl = document.getElementById('search-results');
            const countEl = document.getElementById('search-count');
            const navEl = document.getElementById('search-nav');
            const clearBtn = document.getElementById('search-clear');

            clearBtn.classList.toggle('visible', query.length > 0);

            if (matches.length === 0) {{
                resultsEl.classList.remove('visible');
                countEl.classList.remove('visible');
                navEl.classList.remove('visible');
                if (query) {{
                    countEl.textContent = 'No results found';
                    countEl.classList.add('visible');
                }}
                return;
            }}

            countEl.textContent = `Found ${{matches.length}} result${{matches.length > 1 ? 's' : ''}}`;
            countEl.classList.add('visible');
            navEl.classList.add('visible');

            // Build results list
            let html = '';
            matches.forEach((node, index) => {{
                const nodeType = node.data.type === 'skill' ? 'skill' : 'category';
                html += `
                    <div class="search-result-item${{index === currentMatchIndex ? ' active' : ''}}" data-index="${{index}}">
                        <div class="search-result-name">
                            ${{escapeHtml(node.data.name)}}
                            <span class="search-result-type search-result-type--${{nodeType}}">${{nodeType}}</span>
                        </div>
                        <div class="search-result-path">${{escapeHtml(getNodePath(node))}}</div>
                    </div>
                `;
            }});

            resultsEl.innerHTML = html;
            resultsEl.classList.add('visible');

            // Add click handlers
            resultsEl.querySelectorAll('.search-result-item').forEach(item => {{
                item.addEventListener('click', () => {{
                    const index = parseInt(item.dataset.index);
                    jumpToResult(index);
                }});
            }});
        }}

        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        function jumpToResult(index) {{
            if (index < 0 || index >= searchMatches.length) return;

            currentMatchIndex = index;
            const node = searchMatches[index];

            // Expand path to node
            expandToNode(node);

            // Update tree
            update(root);

            // Scroll to node
            scrollToNode(node);

            // Update results list active state
            document.querySelectorAll('.search-result-item').forEach((item, i) => {{
                item.classList.toggle('active', i === index);
            }});

            // Scroll result into view if needed
            const activeResult = document.querySelector('.search-result-item.active');
            if (activeResult) {{
                activeResult.scrollIntoView({{ block: 'nearest' }});
            }}

            updateNavButtons();
        }}

        function updateNavButtons() {{
            const prevBtn = document.getElementById('prev-result');
            const nextBtn = document.getElementById('next-result');

            prevBtn.disabled = currentMatchIndex <= 0;
            nextBtn.disabled = currentMatchIndex >= searchMatches.length - 1;
        }}

        function clearSearch() {{
            const searchInput = document.getElementById('search');
            searchInput.value = '';
            searchMatches = [];
            currentMatchIndex = -1;

            document.getElementById('search-results').classList.remove('visible');
            document.getElementById('search-count').classList.remove('visible');
            document.getElementById('search-nav').classList.remove('visible');
            document.getElementById('search-clear').classList.remove('visible');

            updateSearchHighlights();
        }}

        // Search input handler with debounce
        let searchTimeout;
        document.getElementById('search').addEventListener('input', function(e) {{
            clearTimeout(searchTimeout);
            const query = e.target.value.toLowerCase().trim();

            searchTimeout = setTimeout(() => {{
                searchMatches = searchTree(query);
                currentMatchIndex = searchMatches.length > 0 ? 0 : -1;
                renderSearchResults(searchMatches, query);
                updateSearchHighlights();

                // Auto-expand and scroll to first match
                if (searchMatches.length > 0) {{
                    expandToNode(searchMatches[0]);
                    update(root);
                    scrollToNode(searchMatches[0]);
                }}
            }}, 200);
        }});

        // Clear button
        document.getElementById('search-clear').addEventListener('click', clearSearch);

        // Navigation buttons
        document.getElementById('prev-result').addEventListener('click', () => {{
            if (currentMatchIndex > 0) {{
                jumpToResult(currentMatchIndex - 1);
            }}
        }});

        document.getElementById('next-result').addEventListener('click', () => {{
            if (currentMatchIndex < searchMatches.length - 1) {{
                jumpToResult(currentMatchIndex + 1);
            }}
        }});

        // Keyboard navigation
        document.getElementById('search').addEventListener('keydown', function(e) {{
            if (searchMatches.length === 0) return;

            if (e.key === 'ArrowDown') {{
                e.preventDefault();
                if (currentMatchIndex < searchMatches.length - 1) {{
                    jumpToResult(currentMatchIndex + 1);
                }}
            }} else if (e.key === 'ArrowUp') {{
                e.preventDefault();
                if (currentMatchIndex > 0) {{
                    jumpToResult(currentMatchIndex - 1);
                }}
            }} else if (e.key === 'Enter') {{
                e.preventDefault();
                if (currentMatchIndex >= 0) {{
                    jumpToResult(currentMatchIndex);
                    document.getElementById('search-results').classList.remove('visible');
                }}
            }} else if (e.key === 'Escape') {{
                document.getElementById('search-results').classList.remove('visible');
            }}
        }});

        // Close results when clicking outside
        document.addEventListener('click', function(e) {{
            if (!e.target.closest('.search-wrapper')) {{
                document.getElementById('search-results').classList.remove('visible');
            }}
        }});

        // Show results when focusing on search with existing query
        document.getElementById('search').addEventListener('focus', function() {{
            if (searchMatches.length > 0) {{
                document.getElementById('search-results').classList.add('visible');
            }}
        }});

        // Expand all on double click root
        svg.selectAll("g.node").filter(d => d.depth === 0)
            .on("dblclick", () => {{
                function expandAll(d) {{
                    if (d._children) {{
                        d.children = d._children;
                        d._children = null;
                    }}
                    if (d.children) d.children.forEach(expandAll);
                }}
                expandAll(root);
                update(root);
            }});
    </script>
</body>
</html>
'''
