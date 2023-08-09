import { StrictMode } from "react";
import NodeList from "./NodeList";
import PieChart from "./PieChart";
import PieData from "./PieData";
import Box from "@mui/material/Box";


export default function Page() {
    return <StrictMode><NodeList /></StrictMode>;
    // return <StrictMode><Box sx={{
    //     width: 600,
    //     height: 600
    // }}><PieChart data={PieData()} /></Box></StrictMode>;

}