import { apiFetchServer } from "@/lib/api-server";
import { SmtpClient, SMTPFormData } from "./SmtpClient";

export default async function SMTPConfigsPage() {
    let initialData: SMTPFormData | null = null;
    try {
        initialData = await apiFetchServer<SMTPFormData>("/config/my-smtp");
    } catch (e) {
        // Silencia erro e deixa o Client component cuidar de falhas ou estado vazio
    }

    return <SmtpClient initialData={initialData} />;
}
