"use client";
import { useState, useEffect } from "react";
import { Search, Briefcase, Calendar, ExternalLink, Building2 } from "lucide-react";

interface Job {
  title: string;
  organization: string;
  category: string;
  url: string;
  source: string;
  date_added: string;
}

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("All");

  useEffect(() => {
    fetch("/jobs.json")
      .then((res) => res.json())
      .then((data) => setJobs(data))
      .catch((err) => console.error("Error loading jobs:", err));
  }, []);

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.organization.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = filterCategory === "All" || job.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-blue-700 text-white p-6 shadow-md">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Briefcase className="w-8 h-8" /> Naukri Radar Pro
          </h1>
          <p className="mt-2 text-blue-100">Latest Sarkari Jobs, Results & Admit Cards in one place.</p>
        </div>
      </header>

      <div className="max-w-5xl mx-auto p-6">
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by job title or organization..."
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <select
            className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white"
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
          >
            <option value="All">All Categories</option>
            <option value="Latest Job">Latest Jobs</option>
            <option value="Result">Results</option>
            <option value="Admit Card">Admit Cards</option>
          </select>
        </div>

        <div className="grid gap-4">
          {filteredJobs.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No jobs found matching your criteria.</div>
          ) : (
            filteredJobs.map((job, index) => (
              <div
                key={index}
                className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-blue-700 mb-1">{job.title}</h3>
                  <div className="flex flex-wrap gap-3 text-sm text-gray-600">
                    <span className="flex items-center gap-1">
                      <Building2 className="w-4 h-4" /> {job.organization}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" /> Added: {job.date_added}
                    </span>
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                      {job.category}
                    </span>
                  </div>
                </div>
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium transition-colors shrink-0"
                >
                  View Details <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}