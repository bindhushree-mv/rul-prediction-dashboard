import { useState, useEffect, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const API = "http://ec2-34-229-201-80.compute-1.amazonaws.com/api";
const WS  = "ws://ec2-34-229-201-80.compute-1.amazonaws.com/ws/stream";

function getRulColor(rul) {
  if (rul === null || rul === undefined) return "#6b7280";
  if (rul <= 30) return "#ef4444";
  if (rul <= 60) return "#f59e0b";
  return "#22c55e";
}

function RulGauge({ rul }) {
  const color = getRulColor(rul);
  const pct = rul === null ? 0 : Math.min((rul / 125) * 100, 100);
  return (
    <div style={{textAlign:"center",padding:"1.5rem"}}>
      <div style={{fontSize:"72px",fontWeight:"700",color,lineHeight:1,marginBottom:"8px"}}>
        {rul !== null ? Math.round(rul) : "--"}
      </div>
      <div style={{fontSize:"14px",color:"#9ca3af",marginBottom:"12px"}}>cycles remaining</div>
      <div style={{height:"8px",background:"#374151",borderRadius:"4px",overflow:"hidden"}}>
        <div style={{height:"100%",width:`${pct}%`,background:color,borderRadius:"4px",transition:"all 0.5s ease"}}/>
      </div>
      <div style={{marginTop:"8px",fontSize:"12px",fontWeight:"600",
        color:rul<=30?"#ef4444":rul<=60?"#f59e0b":"#22c55e"}}>
        {rul===null?"Waiting for data...":
         rul<=30?"CRITICAL — Immediate maintenance required":
         rul<=60?"WARNING — Schedule maintenance soon":
         "NORMAL — Engine healthy"}
      </div>
    </div>
  );
}

function StatCard({ label, value, unit, color }) {
  return (
    <div style={{background:"#1f2937",borderRadius:"12px",padding:"1rem 1.25rem",flex:1,minWidth:"120px"}}>
      <div style={{fontSize:"12px",color:"#9ca3af",marginBottom:"4px"}}>{label}</div>
      <div style={{fontSize:"24px",fontWeight:"600",color:color||"#f9fafb"}}>
        {value??"--"}{unit&&<span style={{fontSize:"13px",color:"#6b7280"}}> {unit}</span>}
      </div>
    </div>
  );
}

export default function App() {
  const [status,setStatus]     = useState(null);
  const [latest,setLatest]     = useState(null);
  const [history,setHistory]   = useState([]);
  const [alerts,setAlerts]     = useState([]);
  const [wsStatus,setWsStatus] = useState("Connecting...");
  const wsRef = useRef(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS);
      wsRef.current = ws;
      ws.onopen = () => setWsStatus("Live");
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "history") {
          const readings = msg.readings || [];
          setHistory(readings.slice(-60));
          if (readings.length > 0) {
            setLatest(readings[readings.length - 1]);
          }
          return;
        }
        setLatest(prev => {
          if (prev && prev.unit_id !== msg.unit_id) {
            setHistory([msg]);
          } else {
            setHistory(h => [...h, msg].slice(-60));
          }
          return msg;
        });
      };
      ws.onclose = () => {
        setWsStatus("Reconnecting...");
        let delay = 3000;
        const retry = () => {
          delay = Math.min(delay * 1.5, 30000);
          setTimeout(connect, delay);
        };
        retry();
      };
      ws.onerror = () => ws.close();
    }
    connect();
    return () => wsRef.current?.close();
  }, []);

  useEffect(() => {
    async function fetchData() {
      try {
        const [s,a] = await Promise.all([
          fetch(`${API}/status`).then(r=>r.json()),
          fetch(`${API}/alerts`).then(r=>r.json()),
        ]);
        setStatus(s);
        setAlerts(a.alerts||[]);
      } catch(e) { console.error(e); }
    }
    fetchData();
    const id = setInterval(fetchData, 10000);
    return () => clearInterval(id);
  }, []);

  const rul      = latest?.predicted_RUL ?? null;
  const rulColor = getRulColor(rul);

  const chartData = history.map(r => ({
    cycle : r.cycle,
    RUL   : r.predicted_RUL ? Math.round(r.predicted_RUL) : null,
    s2    : r.sensors?.s2  != null ? +r.sensors.s2.toFixed(3)  : null,
    s11   : r.sensors?.s11 != null ? +r.sensors.s11.toFixed(3) : null,
    s12   : r.sensors?.s12 != null ? +r.sensors.s12.toFixed(3) : null,
  }));

  const tt = {
    contentStyle:{background:"#111827",border:"1px solid #374151"},
    labelStyle:{color:"#9ca3af"}
  };

  const isConnecting = !latest && wsStatus === "Connecting...";

  return (
    <div style={{minHeight:"100vh",background:"#111827",color:"#f9fafb",
      fontFamily:"system-ui,sans-serif",padding:"1.5rem"}}>

      {isConnecting && (
        <div style={{
          position:"fixed",top:0,left:0,right:0,
          background:"#f59e0b",color:"#000",
          textAlign:"center",padding:"8px",
          fontSize:"13px",fontWeight:"500",zIndex:999
        }}>
          Connecting to live data stream...
        </div>
      )}

      <div style={{display:"flex",justifyContent:"space-between",
        alignItems:"center",marginBottom:"1.5rem"}}>
        <div>
          <h1 style={{margin:0,fontSize:"22px",fontWeight:"600"}}>
            Jet Engine RUL Dashboard
          </h1>
          <p style={{margin:"4px 0 0",fontSize:"13px",color:"#9ca3af"}}>
            NASA CMAPSS FD001 — Live Predictive Maintenance
          </p>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:"8px",fontSize:"13px",
          color:wsStatus==="Live"?"#22c55e":"#f59e0b"}}>
          <div style={{width:"8px",height:"8px",borderRadius:"50%",
            background:wsStatus==="Live"?"#22c55e":"#f59e0b"}}/>
          {wsStatus}
        </div>
      </div>

      <div style={{display:"flex",gap:"12px",marginBottom:"1.5rem",flexWrap:"wrap"}}>
        <StatCard label="Engine unit"    value={latest?.unit_id}                          color="#60a5fa"/>
        <StatCard label="Current cycle"  value={latest?.cycle}         unit="cycles"                   />
        <StatCard label="Predicted RUL"  value={rul!==null?Math.round(rul):null} unit="cycles" color={rulColor}/>
        <StatCard label="Total readings" value={status?.total_readings}                              />
        <StatCard label="Alerts fired"   value={status?.total_alerts}
          color={status?.total_alerts>0?"#ef4444":"#22c55e"}/>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 2fr",gap:"1rem",marginBottom:"1rem"}}>
        <div style={{background:"#1f2937",borderRadius:"12px",padding:"1rem"}}>
          <div style={{fontSize:"13px",color:"#9ca3af",marginBottom:"0.5rem",fontWeight:"500"}}>
            Remaining Useful Life
          </div>
          <RulGauge rul={rul}/>
        </div>
        <div style={{background:"#1f2937",borderRadius:"12px",padding:"1rem"}}>
          <div style={{fontSize:"13px",color:"#9ca3af",marginBottom:"0.75rem",fontWeight:"500"}}>
            RUL over time — last 60 readings
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151"/>
              <XAxis dataKey="cycle" stroke="#6b7280" tick={{fontSize:11}}/>
              <YAxis stroke="#6b7280" tick={{fontSize:11}} domain={[0,125]}/>
              <Tooltip {...tt}/>
              <Line type="monotone" dataKey="RUL" stroke="#22c55e"
                strokeWidth={2} dot={false} name="Predicted RUL"/>
              <Line type="monotone" dataKey={()=>30} stroke="#ef4444"
                strokeWidth={1} strokeDasharray="5 5" dot={false} name="Alert threshold"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:"1rem",marginBottom:"1rem"}}>
        {[
          {key:"s2", label:"Sensor s2",  color:"#60a5fa"},
          {key:"s11",label:"Sensor s11", color:"#a78bfa"},
          {key:"s12",label:"Sensor s12", color:"#34d399"},
        ].map(({key,label,color})=>(
          <div key={key} style={{background:"#1f2937",borderRadius:"12px",padding:"1rem"}}>
            <div style={{fontSize:"13px",color:"#9ca3af",marginBottom:"0.75rem",fontWeight:"500"}}>
              {label} (normalised)
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151"/>
                <XAxis dataKey="cycle" stroke="#6b7280" tick={{fontSize:10}}/>
                <YAxis stroke="#6b7280" tick={{fontSize:10}}/>
                <Tooltip {...tt}/>
                <Line type="monotone" dataKey={key} stroke={color}
                  strokeWidth={1.5} dot={false}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>

      <div style={{background:"#1f2937",borderRadius:"12px",padding:"1rem"}}>
        <div style={{fontSize:"13px",color:"#9ca3af",marginBottom:"0.75rem",fontWeight:"500"}}>
          Alert log
        </div>
        {alerts.length===0?(
          <div style={{color:"#6b7280",fontSize:"13px",padding:"0.5rem 0"}}>
            No alerts yet — all engines nominal
          </div>
        ):(
          <table style={{width:"100%",fontSize:"13px",borderCollapse:"collapse"}}>
            <thead>
              <tr style={{color:"#9ca3af",borderBottom:"1px solid #374151"}}>
                <th style={{textAlign:"left",padding:"6px 8px"}}>Engine</th>
                <th style={{textAlign:"left",padding:"6px 8px"}}>RUL at alert</th>
                <th style={{textAlign:"left",padding:"6px 8px"}}>Cycle</th>
                <th style={{textAlign:"left",padding:"6px 8px"}}>Time</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a,i)=>(
                <tr key={i} style={{borderBottom:"1px solid #374151"}}>
                  <td style={{padding:"6px 8px",color:"#f87171"}}>Engine {a.unit_id}</td>
                  <td style={{padding:"6px 8px",color:"#ef4444",fontWeight:"600"}}>
                    {Math.round(a.rul)} cycles
                  </td>
                  <td style={{padding:"6px 8px"}}>{a.cycle}</td>
                  <td style={{padding:"6px 8px",color:"#6b7280"}}>
                    {new Date(a.time).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
