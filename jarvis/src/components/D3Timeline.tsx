import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { Calendar, AlertCircle, CheckCircle, Clock } from "lucide-react";

interface Milestone {
  id: string;
  projectId: string;
  projectName: string;
  title: string;
  date: Date;
  status: "completed" | "pending" | "critical";
  category: string;
}

const INITIAL_MILESTONES: Milestone[] = [
  {
    id: "m1",
    projectId: "proj-1",
    projectName: "Kampala Clinic Scraping",
    title: "Places API Search Set",
    date: new Date("2026-07-14"),
    status: "completed",
    category: "Scraping"
  },
  {
    id: "m2",
    projectId: "proj-2",
    projectName: "SaaS Multi-Agent Architect",
    title: "Lazy AI Initialization",
    date: new Date("2026-07-16"),
    status: "completed",
    category: "AI Engine"
  },
  {
    id: "m3",
    projectId: "proj-1",
    projectName: "Kampala Clinic Scraping",
    title: "Clinic Schema Parsing",
    date: new Date("2026-07-18"),
    status: "pending",
    category: "Scraping"
  },
  {
    id: "m4",
    projectId: "proj-2",
    projectName: "SaaS Multi-Agent Architect",
    title: "SSE Stream Calibrations",
    date: new Date("2026-07-21"),
    status: "critical",
    category: "AI Engine"
  },
  {
    id: "m5",
    projectId: "proj-1",
    projectName: "Kampala Clinic Scraping",
    title: "Intro Outreach Campaigns",
    date: new Date("2026-07-24"),
    status: "pending",
    category: "Outreach"
  },
  {
    id: "m6",
    projectId: "proj-2",
    projectName: "SaaS Multi-Agent Architect",
    title: "Audio Translation Models",
    date: new Date("2026-07-28"),
    status: "pending",
    category: "AI Engine"
  }
];

export default function D3Timeline() {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 180 });
  const [hoveredMilestone, setHoveredMilestone] = useState<Milestone | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Handle responsive resize via ResizeObserver
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({
          width: Math.max(width, 280),
          height: Math.max(height, 180)
        });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Render D3 Timeline
  useEffect(() => {
    if (!svgRef.current || dimensions.width === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 25, right: 30, bottom: 30, left: 30 };
    const width = dimensions.width - margin.left - margin.right;
    const height = dimensions.height - margin.top - margin.bottom;

    // Time scale
    const dates = INITIAL_MILESTONES.map((m) => m.date.getTime());
    const minDate = new Date(Math.min(...dates) - 24 * 60 * 60 * 1000 * 2); // 2 days padding
    const maxDate = new Date(Math.max(...dates) + 24 * 60 * 60 * 1000 * 2); // 2 days padding

    const xScale = d3.scaleTime()
      .domain([minDate, maxDate])
      .range([0, width]);

    // Center vertical line for the main axis timeline
    const centerY = height / 2;

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    // Draw grid background ticks
    const xTicks = xScale.ticks(5);
    g.selectAll(".grid-line")
      .data(xTicks)
      .enter()
      .append("line")
      .attr("class", "grid-line")
      .attr("x1", (d) => xScale(d))
      .attr("y1", 0)
      .attr("x2", (d) => xScale(d))
      .attr("y2", height)
      .attr("stroke", "rgba(255, 255, 255, 0.05)")
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "2,2");

    // Draw main axis line
    g.append("line")
      .attr("x1", 0)
      .attr("y1", centerY)
      .attr("x2", width)
      .attr("y2", centerY)
      .attr("stroke", "rgba(255, 255, 255, 0.15)")
      .attr("stroke-width", 2);

    // Draw milestone connection lines and nodes
    INITIAL_MILESTONES.forEach((m, idx) => {
      const cx = xScale(m.date);
      // Alternating offsets to prevent overlaps
      const isUpper = idx % 2 === 0;
      const cy = isUpper ? centerY - 35 : centerY + 35;

      const color = m.status === "completed" 
        ? "#10b981" // green
        : m.status === "critical"
        ? "#ef4444" // red
        : "#f59e0b"; // yellow

      // Connecting line
      g.append("line")
        .attr("x1", cx)
        .attr("y1", centerY)
        .attr("x2", cx)
        .attr("y2", cy)
        .attr("stroke", "rgba(255, 255, 255, 0.15)")
        .attr("stroke-width", 1)
        .attr("stroke-dasharray", "2,2");

      // Draw node circle backing
      g.append("circle")
        .attr("cx", cx)
        .attr("cy", cy)
        .attr("r", 7)
        .attr("fill", "#0f172a")
        .attr("stroke", color)
        .attr("stroke-width", 2)
        .attr("class", "cursor-pointer transition-all duration-300 hover:scale-125")
        .style("filter", `drop-shadow(0px 0px 4px ${color}40)`)
        .on("mouseenter", (event) => {
          setHoveredMilestone(m);
          setTooltipPos({
            x: cx + margin.left,
            y: cy + margin.top + (isUpper ? -75 : 15)
          });
        })
        .on("mouseleave", () => {
          setHoveredMilestone(null);
        });

      // Draw active pulsing inner circle if critical or pending
      if (m.status !== "completed") {
        g.append("circle")
          .attr("cx", cx)
          .attr("cy", cy)
          .attr("r", 3)
          .attr("fill", color)
          .attr("class", "animate-ping")
          .style("pointer-events", "none");
      } else {
        // Draw small inner circle
        g.append("circle")
          .attr("cx", cx)
          .attr("cy", cy)
          .attr("r", 3)
          .attr("fill", color)
          .style("pointer-events", "none");
      }

      // Add a clean display label (date abbreviation + abbreviated text)
      const formattedDate = m.date.toLocaleDateString([], { month: "short", day: "numeric" });
      g.append("text")
        .attr("x", cx)
        .attr("y", isUpper ? cy - 12 : cy + 20)
        .attr("text-anchor", "middle")
        .attr("fill", "rgba(255, 255, 255, 0.7)")
        .attr("font-size", "8px")
        .attr("font-family", "monospace")
        .text(formattedDate);

      g.append("text")
        .attr("x", cx)
        .attr("y", isUpper ? cy - 22 : cy + 30)
        .attr("text-anchor", "middle")
        .attr("fill", "#ffffff")
        .attr("font-size", "9px")
        .attr("font-weight", "bold")
        .attr("class", "truncate")
        .style("max-width", "50px")
        .text(m.title.length > 10 ? m.title.substring(0, 8) + ".." : m.title);
    });

  // Performance Optimization: Exclude `hoveredMilestone` from dependencies so hovering over timeline
  // nodes doesn't tear down and rebuild the entire D3 SVG DOM tree on every mouseenter/mouseleave event.
  // OPTIMIZATION: Omit `hoveredMilestone` from dependencies to prevent full D3 SVG DOM teardown
  // and re-creation (via svg.selectAll("*").remove()) on every hover event. Hover state only affects
  // the React JSX overlay tooltip above the canvas.
  }, [dimensions]);

  return (
    <div ref={containerRef} className="relative w-full h-full flex flex-col justify-between">
      {/* Visual Canvas */}
      <div className="flex-1 min-h-0 relative">
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
          className="overflow-visible"
        />

        {/* Floating details tooltip overlay */}
        {hoveredMilestone && (
          <div
            className="absolute z-50 bg-slate-950 border border-slate-800 rounded-lg p-3 shadow-xl w-56 text-left pointer-events-none transition-all duration-150 backdrop-blur-md"
            style={{
              left: `${tooltipPos.x}px`,
              top: `${tooltipPos.y}px`,
              transform: "translate(-50%, -50%)"
            }}
          >
            <div className="flex justify-between items-start mb-1.5">
              <span className="text-[9px] font-mono font-bold tracking-widest text-slate-500 uppercase">
                {hoveredMilestone.category}
              </span>
              <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded border uppercase tracking-wider font-semibold ${
                hoveredMilestone.status === "completed" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                hoveredMilestone.status === "critical" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                "bg-amber-500/10 text-amber-400 border-amber-500/20"
              }`}>
                {hoveredMilestone.status}
              </span>
            </div>
            <div className="text-xs font-bold text-white mb-1">{hoveredMilestone.title}</div>
            <div className="text-[10px] text-slate-400 truncate mb-2">{hoveredMilestone.projectName}</div>
            <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-500 border-t border-slate-900 pt-2">
              <Calendar className="w-3 h-3 text-slate-500" />
              <span>DEADLINE: {hoveredMilestone.date.toLocaleDateString()}</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer Metrics */}
      <div className="pt-2 border-t border-white/5 flex justify-between text-[9px] uppercase font-mono text-slate-500 mt-2 shrink-0">
        <div className="flex gap-3">
          <span className="flex items-center gap-1">
            <CheckCircle className="w-2.5 h-2.5 text-emerald-500" /> COMPLETED
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-2.5 h-2.5 text-amber-500" /> PENDING
          </span>
          <span className="flex items-center gap-1">
            <AlertCircle className="w-2.5 h-2.5 text-rose-500" /> CRITICAL
          </span>
        </div>
        <span className="text-white font-bold">ACTIVE: 6</span>
      </div>
    </div>
  );
}
