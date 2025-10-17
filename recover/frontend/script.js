const mapDiv = document.getElementById("map");
const trendDiv = document.getElementById("trendChart").getContext("2d");
const summaryDiv = document.getElementById("summary");
const alertsDiv = document.getElementById("alerts");
const predictionResult = document.getElementById("predictionResult");

// Fetch heatmap
async function loadHeatmap(){
    try {
        const res = await fetch("http://127.0.0.1:8000/heatmap-data");
        const cities = await res.json();
        mapDiv.innerHTML="";
        cities.forEach(city=>{
            const div=document.createElement("div");
            div.classList.add("city");
            if(city.risk>=0.8) div.classList.add("high");
            else if(city.risk>=0.5) div.classList.add("medium");
            else div.classList.add("low");
            div.textContent=`${city.city}: ${city.risk}`;
            div.onclick=()=> loadTrend(city.city);
            div.onmouseover=()=> showCityInfo(city.city);
            mapDiv.appendChild(div);
        });
    } catch(err){
        mapDiv.textContent="Failed to load cities.";
        console.error(err);
    }
}

// Load trend chart
let chart;
async function loadTrend(cityName){
    try{
        const res=await fetch(`http://127.0.0.1:8000/trend?city=${cityName}`);
        const data=await res.json();
        const labels=data.map(d=>d.date);
        const scores=data.map(d=>d.risk_score);

        if(chart) chart.destroy();
        chart=new Chart(trendDiv,{
            type:"line",
            data:{
                labels:labels,
                datasets:[{
                    label:`${cityName} Risk Trend`,
                    data:scores,
                    borderColor:"#0052cc",
                    backgroundColor:"rgba(0,82,204,0.2)",
                    fill:true,
                    tension:0.3
                }]
            },
            options:{
                responsive:true,
                scales:{
                    y:{min:0,max:1,title:{display:true,text:"Risk Score"}},
                    x:{title:{display:true,text:"Date"}}
                }
            }
        });
    }catch(err){ console.error(err);}
}

// Load summary
async function loadSummary(){
    try{
        const res=await fetch("http://127.0.0.1:8000/summary");
        const data=await res.json();
        summaryDiv.innerHTML=`<div class="p-3 text-center bg-light rounded">
            <strong>Highest Risk City:</strong> ${data.highest_risk_city.city} (${data.highest_risk_city.risk})<br>
            <strong>Average Risk:</strong> ${data.average_risk}<br>
            <strong>Total Cities:</strong> ${data.total_cities}
        </div>`;
    }catch(err){ console.error(err);}
}

// Load alerts
async function loadAlerts(){
    try{
        const res=await fetch("http://127.0.0.1:8000/alerts");
        const data=await res.json();
        if(data.count>0){
            alertsDiv.innerHTML=`<div class="p-3 text-center bg-danger text-white rounded">
                ⚠️ High Risk Cities: ${data.alerts.map(c=>c.city+"("+c.risk+")").join(", ")}
            </div>`;
        }else alertsDiv.innerHTML="";
    }catch(err){ console.error(err);}
}

// City Info tooltip (console)
async function showCityInfo(city){
    try{
        const res=await fetch(`http://127.0.0.1:8000/city-info?city=${city}`);
        const data=await res.json();
        console.log(`City Info: ${city}`, data);
    }catch(err){ console.error(err);}
}

// Predict Risk form
document.getElementById("predictForm").addEventListener("submit",async e=>{
    e.preventDefault();
    const city=document.getElementById("cityInput").value;
    const date=document.getElementById("dateInput").value;
    try{
        const res=await fetch("http://127.0.0.1:8000/predict-risk",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({city,date})
        });
        const data=await res.json();
        predictionResult.innerHTML=`<div class="p-3 bg-info text-white rounded">
            Predicted Risk for ${data.city} on ${data.date}: ${data.predicted_risk}
        </div>`;
    }catch(err){
        predictionResult.innerHTML=`<div class="p-3 bg-danger text-white rounded">
            Failed to fetch predicted risk.
        </div>`;
        console.error(err);
    }
});

// Initial load
loadHeatmap();
loadSummary();
loadAlerts();
