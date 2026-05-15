import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { useRoutes } from "react-router-dom";
import { routes } from "./router";

export default function App() {
  const element = useRoutes(routes);

  return (
    <ConfigProvider locale={zhCN}>
      {element}
    </ConfigProvider>
  );
}
