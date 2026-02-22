import Link from "next/link";

export default function Home() {
  return (
    <div className="text-center py-16">
      <h1 className="text-3xl font-bold mb-4">BVMW SendHub</h1>
      <p className="text-gray-500 mb-8">Interne Planungs- &amp; Freigabe-Plattform für Email-Aussendungen</p>
      <div className="flex gap-4 justify-center flex-wrap">
        <Link href="/calendar" className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Kalender
        </Link>
        <Link href="/requests/new" className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700">
          Neue Anfrage
        </Link>
        <Link href="/requests" className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700">
          Meine Anfragen
        </Link>
      </div>
    </div>
  );
}
