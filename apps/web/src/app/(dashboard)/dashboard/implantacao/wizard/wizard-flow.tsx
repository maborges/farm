"use client";

import React, { useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  Handle,
  Position,
  Node,
  Edge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, AlertTriangle, PlayCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

export type BpmnNodeData = {
  title: string;
  description: string;
  status: "COMPLETED" | "ACTIVE" | "BLOCKED";
  link?: string | null;
  actionLabel?: string;
};

function CustomBpmnNode({ data }: { data: BpmnNodeData }) {
  const isCompleted = data.status === "COMPLETED";
  const isBlocked = data.status === "BLOCKED";
  const isActive = data.status === "ACTIVE";

  return (
    <div className="relative group">
      <Handle type="target" position={Position.Left} className="w-2 h-2 bg-slate-300 border-none" />

      <Card className={cn("rounded-lg shadow-sm border w-[280px] transition-all duration-300", 
        isCompleted ? "border-emerald-200 bg-emerald-50/40" : 
        isActive ? "border-blue-400 bg-white ring-4 ring-blue-500/20 shadow-lg shadow-blue-500/10 z-10" :
        "border-slate-200 bg-slate-50/50 opacity-70"
      )}>
        <CardContent className="p-4 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-3">
            <div className={cn("font-bold text-sm leading-tight", isCompleted ? "text-emerald-900" : isActive ? "text-slate-900" : "text-slate-500")}>{data.title}</div>
            {isCompleted ? (
              <CheckCircle2 className="size-5 text-emerald-500 shrink-0 mt-0.5" />
            ) : isBlocked ? (
              <AlertTriangle className="size-5 text-slate-400 shrink-0 mt-0.5" />
            ) : (
              <PlayCircle className="size-5 text-blue-500 shrink-0 mt-0.5 animate-pulse" />
            )}
          </div>
          
          {data.description && (
            <p className="text-[12px] text-slate-500 leading-relaxed line-clamp-2">{data.description}</p>
          )}

          {isActive && data.link && !isBlocked && (
            <Button asChild size="sm" className="mt-2 w-full" variant="default">
              <Link href={data.link}>{data.actionLabel || "Iniciar Tarefa"}</Link>
            </Button>
          )}
          {isCompleted && data.link && (
            <Button asChild size="sm" className="mt-2 w-full" variant="outline">
              <Link href={data.link}>Revisar</Link>
            </Button>
          )}
          {isBlocked && (
            <Button size="sm" disabled className="mt-2 w-full" variant="outline">
              Bloqueado por pré-requisito
            </Button>
          )}
        </CardContent>
      </Card>

      <Handle type="source" position={Position.Right} className="w-2 h-2 bg-slate-300 border-none" />
    </div>
  );
}

const nodeTypes = {
  bpmnNode: CustomBpmnNode,
};

const edgeOptions = {
  type: 'smoothstep',
  markerEnd: {
    type: MarkerType.ArrowClosed,
    color: '#cbd5e1',
  },
  style: {
    strokeWidth: 2,
    stroke: '#cbd5e1',
  },
};

export function WizardFlow({ initialNodes, initialEdges }: { initialNodes: Node[], initialEdges: Edge[] }) {
  const memoizedNodeTypes = useMemo(() => nodeTypes, []);

  return (
    <div className="w-full min-h-[600px] h-[calc(100vh-280px)] bg-white border-t border-slate-200">
      <ReactFlow
        nodes={initialNodes}
        edges={initialEdges}
        nodeTypes={memoizedNodeTypes}
        defaultEdgeOptions={edgeOptions}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.2}
        nodesDraggable={false}
        nodesConnectable={false}
        panOnScroll={true}
        panOnDrag={true}
      >
        <Background gap={16} size={1} color="#e2e8f0" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
