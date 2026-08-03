buildCard(candidate) {

    const avatar = this.getInitials(candidate.fullName || "Faculty");

    const pubs =
        Number(candidate.publicationSummary?.journal_publications || 0) +
        Number(candidate.publicationSummary?.conference_publications || 0);

    return `

    <article class="faculty-card">

        <div class="faculty-card-header">

            <div class="faculty-card-left">

                <div class="faculty-card__avatar">

                    ${avatar}

                </div>

                <div>

                    <h3>${candidate.fullName || "Faculty"}</h3>

                    <div class="designation">
                        ${candidate.designation || "Faculty"}
                    </div>

                </div>

            </div>

            <span class="degree-badge">
                ${candidate.highestDegree || "Degree"}
            </span>

        </div>

        <div class="mini-stats">

            <div class="mini-card">
                <span class="mini-value">${candidate.experienceYears || 0}</span>
                <span class="mini-label">Years</span>
            </div>

            <div class="mini-card">
                <span class="mini-value">${pubs}</span>
                <span class="mini-label">Publications</span>
            </div>

            <div class="mini-card">
                <span class="mini-value">
                    ${candidate.instituteType || "University"}
                </span>
                <span class="mini-label">Institute</span>
            </div>

        </div>

        <button
            class="view-btn"
            onclick="window.location.href='faculty.html?id=${candidate.id}'">

            View Details

        </button>

    </article>

    `;
}